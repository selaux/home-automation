"""Handle radio connection with the nrf24 modules"""

import os
try:
    from nrf24 import NRF24
except(RuntimeError, ImportError) as error:
    if 'TEST_ENV' in os.environ:
        print("Assuming test-environment")
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

MAX_PAYLOAD_SIZE = 27

class Radio():
    """Wrapper around the nrf24 radio including client_id and crypto handling"""

    def __init__(self):
        """Setup the radio module"""
        self.server_address = SERVER_ADDRESS
        self.server_id = SERVER_ID
        self.client_ids_to_addresses = {}
        self.client_ids_to_counters = {}

        self.nrf24 = NRF24()
        self.nrf24.begin(0, 0, 25, 24)

        self.nrf24.setRetries(15, 15)
        self.nrf24.setPayloadSize(32)
        self.nrf24.setChannel(0x4c)
        self.nrf24.setDataRate(NRF24.BR_1MBPS)
        self.nrf24.setPALevel(NRF24.PA_HIGH)
        self.nrf24.setCRCLength(NRF24.CRC_16)
        self.nrf24.setAutoAck(True)
        self.nrf24.enableAckPayload()
        self.nrf24.openReadingPipe(1, self.server_address)
        self.nrf24.openWritingPipe(self.server_address)
        self.nrf24.startListening()

        self.nrf24.printDetails()

    def send_packet(self, client_id, packet_id, payload):
        """Send packet to a client"""
        address = self.client_ids_to_addresses[client_id]
        payload_size = len(payload)
        padded_packet = [randint(0, 255) for dummy in range(0, MAX_PAYLOAD_SIZE - payload_size)]
        padded_packet[:0] = payload

        packed = pack('BBBB28s', 1, 0, packet_id, payload_size, bytes(padded_packet))
        encrypted = encrypt_packet(bytes(packed))

        self.nrf24.stopListening()
        self.nrf24.openReadingPipe(1, self.server_address)
        self.nrf24.openWritingPipe(address)
        success = self.nrf24.write(encrypted)
        self.nrf24.startListening()
        if not success:
            print("Failed sending packet!")
        return success

    def is_packet_available(self):
        """Check wether a packet is available, write ACK-payload otherwise"""
        ack_payload = bytes(self.server_id)

        if not self.nrf24.available():
            self.nrf24.writeAckPayload(1, ack_payload, 8)
            return False
        return True

    def get_packet(self):
        """Get available packet from radio, if it is a registration packet handle it before passing on"""
        encrypted_packet = []
        self.nrf24.read(encrypted_packet, 32)
        decrypted_packet = decrypt_packet(encrypted_packet)

        client_id, message_id, payload_length = unpack('BBB', decrypted_packet[1:4])
        counter = unpack('H', decrypted_packet[-1:] + decrypted_packet[:1])[0]
        payload = decrypted_packet[4:(4+payload_length)]

        if message_id == 0:
            client_id = self.handle_registration_message(counter, payload)

        return client_id, message_id, payload

    def get_client_id(self, address):
        """Get a client id for a specific address"""
        for client_id, stored_address in self.client_ids_to_addresses.items():
            if bytes(stored_address) == bytes(address):
                return client_id

        for i in range(1, 255):
            if not i in self.client_ids_to_addresses:
                return i

        return False

    def handle_registration_message(self, counter, payload):
        """Handle the registration of a client without client_id"""
        address = list(unpack('<BBBBB', payload[:5])[::-1])
        new_client_id = self.get_client_id(address)

        self.client_ids_to_addresses[new_client_id] = address
        self.client_ids_to_counters[new_client_id] = counter

        return new_client_id
