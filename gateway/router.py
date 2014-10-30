"""Handle the connection between clients and message queue"""

import asyncio
import logging
import asynqp
from crypto import xor_checksum
from struct import pack, unpack
from settings import SERVER_ID, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, \
    RABBITMQ_VIRTUAL_HOST
from constants import PacketTypes

SERVER_ID_CHECKSUM = xor_checksum(SERVER_ID)

EXCHANGE = 'gateway.exchange'
QUEUE = 'gateway.queue'

LOGGER = logging.getLogger(__name__)


class Router():
    """Handle packets coming from the clients / message_queue and route them from/to the clients"""

    def __init__(self):
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None
        self.consumer = None
        self.send_packet = None
        self.subscriptions = {}

    def set_send_packet(self, send_packet):
        """Set the function to send a packet over the radio"""
        self.send_packet = send_packet

    @asyncio.coroutine
    def connect_to_message_queue(self):
        """Connects to the amqp exchange and queue"""
        def log_returned_message(dummy):
            """Log when message has no handler in message queue"""
            LOGGER.info("Nobody cared for {0}".format(dummy.json()))

        self.connection = yield from asynqp.connect(
            RABBITMQ_HOST,
            RABBITMQ_PORT,
            RABBITMQ_USERNAME,
            RABBITMQ_PASSWORD,
            RABBITMQ_VIRTUAL_HOST
        )
        self.channel = yield from self.connection.open_channel()
        self.channel.set_return_handler(log_returned_message)
        self.exchange = yield from self.channel.declare_exchange(EXCHANGE, 'fanout')
        self.queue = yield from self.channel.declare_queue(QUEUE, auto_delete=True)
        self.consumer = yield from self.queue.consume(self.handle_message)

    @asyncio.coroutine
    def handle_packet(self, client_id, message_id, payload):
        """Handle a single packet from a nrf24 client"""
        LOGGER.info("Recieving packet type {0} from client {1}".format(message_id, client_id))
        if message_id == PacketTypes.REGISTER:
            yield from self.handle_register_packet(client_id)
        if message_id == PacketTypes.SUB_CHANNEL:
            yield from self.handle_sub_packet(client_id, payload)
        if message_id == 5:
            msg = asynqp.Message({'pong': 'content'})
            self.exchange.publish(msg, 'gateway.pong')

    @asyncio.coroutine
    def handle_register_packet(self, client_id):
        """Handle registration packet"""
        response = pack('B7sB', client_id, bytes(SERVER_ID), SERVER_ID_CHECKSUM)
        self.clear_subscriptions(client_id)
        if self.send_packet:
            yield from asyncio.sleep(0.02)
            self.send_packet(client_id, PacketTypes.REGISTER_SERVER_ACK, response)

    @asyncio.coroutine
    def handle_sub_packet(self, client_id, payload):
        """Handle packet for subscription to a routing key"""
        payload_size = len(payload)
        routing_key_length = str((payload_size-2))
        channel_id, transform_id = unpack('BB', payload[:2])
        routing_key = unpack(routing_key_length + 's', payload[2:])[0].decode('ascii')
        yield from self.add_subscription(client_id, routing_key, channel_id, transform_id)

    @asyncio.coroutine
    def add_subscription(self, client_id, routing_key, channel_id, transform_id):
        """Add subscription object so later messages can be routed correctly"""
        subscription = {
            'client_id': client_id,
            'channel_id': channel_id,
            'transform_id': transform_id
        }
        if routing_key in self.subscriptions:
            self.subscriptions[routing_key].append(subscription)
        else:
            self.subscriptions[routing_key] = [subscription]
        yield from self.queue.bind(self.exchange, routing_key)

    def clear_subscriptions(self, client_id):
        """Clear all subscriptions for a client after new registration"""
        for routing_key in self.subscriptions:
            subscriptions = self.subscriptions[routing_key]
            self.subscriptions[routing_key] = [s for s in subscriptions if s['client_id'] != client_id]

    def handle_message(self, message):
        """Handle message coming from rabbitmq"""
        response = pack('11s', bytes([0]) + bytes('Pong!', 'ascii'))
        LOGGER.info("Receiving message %s", message.json())
        if self.send_packet:
            self.send_packet(1, PacketTypes.PUB, response)
        message.ack()
