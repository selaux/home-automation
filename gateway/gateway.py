"""Should eventually become the gateway between rabbitmq and the sensors/actuators listening on rf24 radio"""

from nrf24 import NRF24
from Crypto.Cipher import AES
import RPi.GPIO as GPIO
import atexit
import struct
import random
import asyncio

KEY = bytes([25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188])
SERVER_ADDRESS = [0xf0, 0xf0, 0xf0, 0xf0, 0xe1]
SERVER_ID = [random.randint(0, 255) for dummy in range(8)]

random.seed()

def initialize_gpio():
    """Initialize GPIO (handles pin numbering and cleanup)"""
    GPIO.setmode(GPIO.BCM)

    @atexit.register
    def dummy_cleanup_gpio():
        """Clean up GPIO pins"""
        print("Cleaning up GPIO before exit")
        GPIO.cleanup()


def initialize_radio():
    """Setup the radio module"""
    radio = NRF24()
    radio.begin(0, 0, 25, 24)

    radio.setRetries(15, 15)
    radio.setPayloadSize(32)
    radio.setChannel(0x4c)
    radio.setDataRate(NRF24.BR_1MBPS)
    radio.setPALevel(NRF24.PA_HIGH)
    radio.setCRCLength(NRF24.CRC_16)
    radio.setAutoAck(True)
    radio.enableAckPayload()

    radio.openReadingPipe(1, SERVER_ADDRESS)
    radio.openWritingPipe(SERVER_ADDRESS)
    radio.startListening()

    radio.printDetails()

    return radio


def decrypt_packet(packet):
    """Decrypt packet for transmission over rf24"""
    cipher = AES.new(KEY, AES.MODE_ECB)

    encrypted_part1 = bytes(packet[0:16])
    encrypted_part2 = bytes(packet[16:32])

    intermediate_part2 = cipher.decrypt(encrypted_part2)
    decrypted_part2 = bytes([e ^ i for e, i in zip(encrypted_part1, intermediate_part2)])
    decrypted_part1 = cipher.decrypt(encrypted_part1)

    return decrypted_part1 + decrypted_part2


def encrypt_packet(packet):
    """Encrypt packet for transmission over rf24"""
    cipher = AES.new(KEY, AES.MODE_ECB)

    decrypted_part1 = bytes(packet[0:16])
    decrypted_part2 = bytes(packet[16:32])

    encrypted_part1 = cipher.encrypt(decrypted_part1)
    intermediate_part2 = bytes([e ^ i for e, i in zip(encrypted_part1, decrypted_part2)])
    encrypted_part2 = cipher.encrypt(intermediate_part2)

    return encrypted_part1 + encrypted_part2

def send_packet(radio, address, packet_id, payload):
    """Send packet to an address"""
    payload_size = len(payload)
    packed = struct.pack('BBBB28s', 1, 0, packet_id, payload_size, payload)
    encrypted = encrypt_packet(bytes(packed))

    radio.stopListening()
    radio.openReadingPipe(1, SERVER_ADDRESS)
    radio.openWritingPipe(address)
    success = radio.write(encrypted)
    radio.startListening()
    if not success:
        print("Failed sending packet!")


@asyncio.coroutine
def handle(radio, packet):
    """Handle decrypted incoming packets from the radio"""
    counter, client_id, message_type = struct.unpack('BBB', packet[:3])
    print("Recieving message type {0} with counter {1}".format(message_type, counter))
    if message_type == 0:
        address = list(struct.unpack('<BBBBBBBBBBBB20s', packet)[4:12][::-1][3:8])
        client_id = random.randint(1, 254)
        print("Register {0} as {1}".format(bytes(address), client_id))
        yield from asyncio.sleep(0.02)
        response = struct.pack('B8s', client_id, bytes(SERVER_ID))
        send_packet(radio, address, 1, response)


@asyncio.coroutine
def run():
    """Poll for radio messages, decrypt them and pass them to the handler"""
    initialize_gpio()
    radio = initialize_radio()
    ack_payload = bytes(SERVER_ID)

    while True:
        if not radio.available():
            radio.writeAckPayload(1, ack_payload, 8)
            yield from asyncio.sleep(0.04)
        else:
            encrypted_packet = []
            radio.read(encrypted_packet, 32)
            message = decrypt_packet(encrypted_packet)
            asyncio.async(handle(radio, bytes(message)))

def main():
    """Runs the gateway"""
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
