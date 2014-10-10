"""Handle radio connection with the nrf24 modules"""

from nrf24 import NRF24
from struct import pack, unpack
from crypto import decrypt_packet, encrypt_packet
from settings import SERVER_ADDRESS, SERVER_ID


class Radio():
    """Wrapper around the nrf24 radio including client_id and crypto handling"""

    def __init__(self):
        """Setup the radio module"""
        self.server_address = SERVER_ADDRESS
        self.server_id = SERVER_ID
        self.client_ids_to_addresses = {}
        self.client_ids_to_counters = {}

        self.radio = NRF24()
        self.radio.begin(0, 0, 25, 24)

        self.radio.setRetries(15, 15)
        self.radio.setPayloadSize(32)
        self.radio.setChannel(0x4c)
        self.radio.setDataRate(NRF24.BR_1MBPS)
        self.radio.setPALevel(NRF24.PA_HIGH)
        self.radio.setCRCLength(NRF24.CRC_16)
        self.radio.setAutoAck(True)
        self.radio.enableAckPayload()

        self.radio.openReadingPipe(1, self.server_address)
        self.radio.openWritingPipe(self.server_address)
        self.radio.startListening()

        self.radio.printDetails()

    def send_packet(self, client_id, packet_id, payload):
        """Send packet to a client"""
        address = self.client_ids_to_addresses[client_id]
        payload_size = len(payload)
        packed = pack('BBBB28s', 1, 0, packet_id, payload_size, payload)
        encrypted = encrypt_packet(bytes(packed))

        self.radio.stopListening()
        self.radio.openReadingPipe(1, self.server_address)
        self.radio.openWritingPipe(address)
        success = self.radio.write(encrypted)
        self.radio.startListening()
        if not success:
            print("Failed sending packet!")

    def is_packet_available(self):
        """Check wether a packet is available, write ACK-payload otherwise"""
        ack_payload = bytes(self.server_id)

        if not self.radio.available():
            self.radio.writeAckPayload(1, ack_payload, 8)
            return False
        return True

    def get_packet(self):
        """Get available packet from radio, if it is a registration packet handle it before passing on"""
        encrypted_packet = []
        self.radio.read(encrypted_packet, 32)
        decrypted_packet = decrypt_packet(encrypted_packet)

        counter, client_id, message_id, payload_length = unpack('BBBB', decrypted_packet[:4])
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
        address = list(unpack('<BBBBBBBB', payload)[::-1][3:8])
        new_client_id = self.get_client_id(address)

        self.client_ids_to_addresses[new_client_id] = address
        self.client_ids_to_counters[new_client_id] = counter

        return new_client_id
