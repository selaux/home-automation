"""Handle the connection between clients and message queue"""

import asyncio
import logging
import asynqp
from crypto import xor_checksum
from struct import pack, unpack
from settings import SERVER_ID, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, \
    RABBITMQ_VIRTUAL_HOST
from transforms import SwitchTransform, TemperatureTransform
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
        self.subscription_channels = {}
        self.publish_channels = {}
        self.transforms = {}
        self.register_transform(0, SwitchTransform)
        self.register_transform(1, TemperatureTransform)

    def register_transform(self, transform_id, transform_class):
        """Register a new transform class with the gateway"""
        self.transforms[transform_id] = transform_class

    def set_send_packet(self, send_packet):
        """Set the function to send a packet over the radio"""
        self.send_packet = send_packet

    @asyncio.coroutine
    def connect_to_message_queue(self):
        """Connects to the amqp exchange and queue"""
        def log_returned_message(message):
            """Log when message has no handler in message queue"""
            LOGGER.info("Nobody cared for {0} {1}".format(message.routing_key, message.json()))

        self.connection = yield from asynqp.connect(
            RABBITMQ_HOST,
            RABBITMQ_PORT,
            RABBITMQ_USERNAME,
            RABBITMQ_PASSWORD,
            RABBITMQ_VIRTUAL_HOST
        )
        self.channel = yield from self.connection.open_channel()
        self.channel.set_return_handler(log_returned_message)
        self.exchange = yield from self.channel.declare_exchange(EXCHANGE, 'topic')
        self.queue = yield from self.channel.declare_queue(QUEUE, auto_delete=True)
        self.consumer = yield from self.queue.consume(self.handle_message)

    @asyncio.coroutine
    def handle_packet(self, client_id, message_id, payload):
        """Handle a single packet from a nrf24 client"""
        LOGGER.info("Recieving packet type {0} from client {1}".format(message_id, client_id))
        if message_id == PacketTypes.REGISTER:
            yield from self.handle_register_packet(client_id)
        if message_id == PacketTypes.PUB_CHANNEL:
            yield from self.handle_pub_channel_packet(client_id, payload)
        if message_id == PacketTypes.SUB_CHANNEL:
            yield from self.handle_sub_channel_packet(client_id, payload)
        if message_id == PacketTypes.PUB:
            self.handle_pub_packet(client_id, payload)

    @asyncio.coroutine
    def handle_register_packet(self, client_id):
        """Handle registration packet"""
        response = pack('B7sB', client_id, bytes(SERVER_ID), SERVER_ID_CHECKSUM)
        self.clear_subscription_channels(client_id)
        self.clear_publish_channels(client_id)
        if self.send_packet:
            yield from asyncio.sleep(0.02)
            self.send_packet(client_id, PacketTypes.REGISTER_SERVER_ACK, response)

    @staticmethod
    def extract_channel_packet_data(payload):
        """Extract payload data from pub- and sub-channel packets"""
        payload_size = len(payload)
        routing_key_length = str((payload_size-2))
        channel_id, transform_id = unpack('BB', payload[:2])
        routing_key = unpack(routing_key_length + 's', payload[2:])[0].decode('ascii')
        return routing_key, channel_id, transform_id

    @asyncio.coroutine
    def handle_pub_channel_packet(self, client_id, payload):
        """Handle packet for creating a publish channel for a routing key"""
        routing_key, channel_id, transform_id = self.extract_channel_packet_data(payload)
        self.add_publish_channel(client_id, routing_key, channel_id, transform_id)

    @asyncio.coroutine
    def handle_sub_channel_packet(self, client_id, payload):
        """Handle packet for a subscription channel to a routing key"""
        routing_key, channel_id, transform_id = self.extract_channel_packet_data(payload)
        yield from self.add_subscription_channel(client_id, routing_key, channel_id, transform_id)

    def handle_pub_packet(self, client_id, payload):
        """Route publish packet from client to message queue"""
        if client_id in self.publish_channels:
            channel_id, = unpack('B', payload[:1])
            channel = next((c for c in self.publish_channels[client_id] if c['channel_id'] == channel_id), None)
            if channel:
                transform = self.transforms[channel['transform_id']]
                routing_key = channel['routing_key']
                msg = asynqp.Message(transform.to_message(payload[1:]))
                self.exchange.publish(msg, routing_key)
            else:
                LOGGER.warning('Client {0} tried to publish message with unknown channel {1}'.format(
                    client_id,
                    channel_id
                ))
        else:
            LOGGER.warning('Client {0} tried to publish, but has no channels set up'.format(client_id))

    @asyncio.coroutine
    def add_subscription_channel(self, client_id, routing_key, channel_id, transform_id):
        """Add subscription object so later messages can be routed correctly"""
        subscription = {
            'client_id': client_id,
            'channel_id': channel_id,
            'transform_id': transform_id
        }
        if transform_id in self.transforms:
            if routing_key in self.subscription_channels:
                self.subscription_channels[routing_key].append(subscription)
            else:
                self.subscription_channels[routing_key] = [subscription]
            yield from self.queue.bind(self.exchange, routing_key)
        else:
            LOGGER.warning('Client {0} tried to register sub-channel {1} with unknown transform {2}'.format(
                client_id,
                channel_id,
                transform_id
            ))

    def clear_subscription_channels(self, client_id):
        """Clear all subscriptions for a client after new registration"""
        for routing_key in self.subscription_channels:
            subscriptions = self.subscription_channels[routing_key]
            self.subscription_channels[routing_key] = [s for s in subscriptions if s['client_id'] != client_id]

    def add_publish_channel(self, client_id, routing_key, channel_id, transform_id):
        """Add a publish_channel object so later packets can be routed correctly"""
        if transform_id in self.transforms:
            publish_channel = {
                'routing_key': routing_key,
                'channel_id': channel_id,
                'transform_id': transform_id
            }
            if client_id in self.publish_channels:
                self.publish_channels[client_id].append(publish_channel)
            else:
                self.publish_channels[client_id] = [publish_channel]
        else:
            LOGGER.warning('Client {0} tried to register pub-channel {1} with unknown transform {2}'.format(
                client_id,
                channel_id,
                transform_id
            ))

    def clear_publish_channels(self, client_id):
        """Clear all publish channels for a client after a new registration"""
        if client_id in self.publish_channels:
            self.publish_channels.pop(client_id)

    def handle_message(self, message):
        """Handle message coming from rabbitmq and route them to the respective clients"""
        routing_key = message.routing_key
        json = message.json()
        LOGGER.info("Receiving message %s %s", routing_key, json)
        if routing_key in self.subscription_channels:
            for channel in self.subscription_channels[routing_key]:
                data = self.transforms[channel['transform_id']].to_packet(json)
                channel_id = pack('B', channel['channel_id'])
                payload = channel_id + data
                if self.send_packet:
                    self.send_packet(channel['client_id'], PacketTypes.PUB, payload)
