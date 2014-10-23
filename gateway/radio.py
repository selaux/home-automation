"""Handle radio connection with the nrf24 modules"""

import os
import logging
try:
    from nrf24 import NRF24
except(RuntimeError, ImportError) as error:
    if 'TEST_ENV' in os.environ:
        LOGGER = logging.getLogger(__name__)
        LOGGER.warn("Assuming test-environment")
        class NRF24:
            """This will be stubbed in tests"""
            def __init__(self):
                pass
    else:
        raise error
from struct import pack, unpack
from random import randint
from crypto import decrypt_packet, encrypt_packet
from settings import SERVER_ADDRESS, SERVER_ID
from constants import PacketTypes

MAX_PAYLOAD_SIZE = 27
MAX_UINT16 = 65535

LOGGER = logging.getLogger(__name__)

class Radio():
    """Wrapper around the nrf24 radio including client_id and crypto handling"""

    def __init__(self):
        """Setup the radio module"""
        self.server_address = SERVER_ADDRESS
        self.server_id = SERVER_ID
        self.clients = []

        self.nrf24 = NRF24()
        self.nrf24.begin(0, 0, 25, 24)

        self.nrf24.setRetries(15, 15)
        self.nrf24.setPayloadSize(32)
        self.nrf24.setChannel(0x4c)
        self.nrf24.setDataRate(NRF24.BR_250KBPS)
        self.nrf24.setPALevel(NRF24.PA_HIGH)
        self.nrf24.setCRCLength(NRF24.CRC_16)
        self.nrf24.setAutoAck(True)
        self.nrf24.enableAckPayload()
        self.nrf24.openReadingPipe(1, self.server_address)
        self.nrf24.openWritingPipe(self.server_address)
        self.nrf24.startListening()

        if LOGGER.isEnabledFor(logging.INFO):
            self.nrf24.printDetails()

    def send_packet(self, client_id, packet_id, payload):
        """Send packet to a client"""
        client = next((c for c in self.clients if c['client_id'] == client_id), None)
        address = client['address']
        counter_bytes = pack('H', client['server_counter'])
        payload_size = len(payload)
        padded_packet = [randint(0, 255) for dummy in range(0, MAX_PAYLOAD_SIZE - payload_size)]
        padded_packet[:0] = payload

        packed = pack('BBBB27sB', counter_bytes[1], 0, packet_id, payload_size, bytes(padded_packet), counter_bytes[0])
        encrypted = encrypt_packet(bytes(packed))

        self.nrf24.stopListening()
        self.nrf24.openReadingPipe(1, self.server_address)
        self.nrf24.openWritingPipe(address)
        success = self.nrf24.write(encrypted)
        self.nrf24.startListening()
        if not success:
            LOGGER.info("Failed sending packet!")
        else:
            client['server_counter'] = client['server_counter']+1 if client['server_counter'] != MAX_UINT16 else 0
        return success

    def get_packet(self):
        """Get available packet from radio, if it is a registration packet handle it before passing on"""
        if not self.nrf24.available():
            ack_payload = bytes(self.server_id)
            self.nrf24.writeAckPayload(1, ack_payload, 8)
            return False

        encrypted_packet = []
        self.nrf24.read(encrypted_packet, 32)
        decrypted_packet = decrypt_packet(encrypted_packet)

        client_id, message_id, payload_length = unpack('BBB', decrypted_packet[1:4])
        received_counter = unpack('H', decrypted_packet[-1:] + decrypted_packet[:1])[0]
        payload_length = min(payload_length, MAX_PAYLOAD_SIZE)
        payload = decrypted_packet[4:(4+payload_length)]

        if message_id == PacketTypes.REGISTER:
            client_id = self.handle_registration_message(received_counter, payload)

        if not self.has_client_id(client_id):
            return False

        if not self.is_counter_is_in_expected_range(client_id, received_counter):
            return False

        client = next((c for c in self.clients if c['client_id'] == client_id), None)
        client['client_counter'] = received_counter

        return client_id, message_id, payload

    def is_counter_is_in_expected_range(self, client_id, received_counter):
        """ Is the received client_counter within the expected range
            Expected range: [last counter + 1, last_counter+10] with respect to the value range of uint8_t
        """
        last_counter = next((c['client_counter'] for c in self.clients if c['client_id'] == client_id))
        maximum = MAX_UINT16
        expected_range = [
            last_counter+i if last_counter+i <= maximum else last_counter+i-maximum-1 for i in range(1, 11)
        ]
        return received_counter in expected_range

    def get_client_id(self, address):
        """Get a client id for a specific address"""
        all_existing_client_ids = [c['client_id'] for c in self.clients]
        existing_client_id = next((c['client_id'] for c in self.clients if c['address'] == address), None)

        if existing_client_id:
            return existing_client_id

        for i in range(1, 255):
            if not i in all_existing_client_ids:
                return i

        return False

    def has_client_id(self, client_id):
        """Does the gateway have this client_id registered"""
        all_existing_client_ids = [c['client_id'] for c in self.clients]
        return client_id in all_existing_client_ids

    def handle_registration_message(self, counter, payload):
        """Handle the registration of a client without client_id"""
        address = list(unpack('<BBBBB', payload[:5])[::-1])
        new_client_id = self.get_client_id(address)

        self.clients = [c for c in self.clients if c['client_id'] is not new_client_id]
        self.clients.append({
            'client_id': new_client_id,
            'address': address,
            'client_counter': counter-1,
            'server_counter': randint(0, MAX_UINT16)
        })

        return new_client_id
