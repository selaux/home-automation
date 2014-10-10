"""Handle the connection between clients and message queue"""

import asyncio
from struct import pack
from settings import SERVER_ID

class Router():
    """Handle packets coming from the clients / message_queue and route them from/to the clients"""

    def __init__(self, send_packet_fn):
        self.send_packet = send_packet_fn

    @asyncio.coroutine
    def handle_packet(self, client_id, message_id, dummy_payload):
        """Handle a single packet from a nrf24 client"""
        print("Recieving message type {0} from client {1}".format(message_id, client_id))
        if message_id == 0:
            response = pack('B8s', client_id, bytes(SERVER_ID))
            yield from asyncio.sleep(0.02)
            self.send_packet(client_id, 1, response)
