"""Handle the connection between clients and message queue"""

import asyncio
import logging
import asynqp
from crypto import xor_checksum
from struct import pack
from settings import SERVER_ID, RABBITMQ_HOST, RABBITMQ_PORT, RABBITMQ_USERNAME, RABBITMQ_PASSWORD, \
    RABBITMQ_VIRTUAL_HOST
from constants import PacketTypes

EXCHANGE = 'gateway.exchange'
QUEUE = 'gateway.queue'

LOGGER = logging.getLogger(__name__)

class Router():
    """Handle packets coming from the clients / message_queue and route them from/to the clients"""

    def __init__(self):
        self.server_id = SERVER_ID
        self.server_id_checksum = xor_checksum(self.server_id)
        self.connection = None
        self.channel = None
        self.exchange = None
        self.queue = None

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
        self.queue = yield from self.channel.declare_queue(QUEUE)

    @asyncio.coroutine
    def handle_packet(self, client_id, message_id, dummy_payload, send_packet):
        """Handle a single packet from a nrf24 client"""
        LOGGER.info("Recieving message type {0} from client {1}".format(message_id, client_id))
        if message_id == PacketTypes.REGISTER:
            response = pack('B7sB', client_id, bytes(self.server_id), self.server_id_checksum)
            yield from asyncio.sleep(0.02)
            send_packet(client_id, 1, response)
