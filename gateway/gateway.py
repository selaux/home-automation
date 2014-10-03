from nrf24 import NRF24
from Crypto.Cipher import AES
import RPi.GPIO as GPIO
import time
import atexit
import struct
import random

KEY = bytes([25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188 ])
SERVER_ADDRESS = [0xf0, 0xf0, 0xf0, 0xf0, 0xe1]

def initializeGPIO():
    GPIO.setmode(GPIO.BCM)

    @atexit.register
    def cleanupGPIO():
        print("Cleaning up GPIO before exit")
        GPIO.cleanup()

def initializeRadio():
    radio = NRF24()
    radio.begin(0, 0, 25, 24)

    radio.setRetries(15, 15)
    radio.setPayloadSize(32)
    radio.setChannel(0x4c)
    radio.setDataRate(NRF24.BR_1MBPS)
    radio.setPALevel(NRF24.PA_LOW)
    radio.setCRCLength(NRF24.CRC_16)
    radio.setAutoAck(1)

    radio.openReadingPipe(1, SERVER_ADDRESS)
    radio.startListening()

    radio.printDetails()

    return radio

def decryptPacket(packet):
    cipher = AES.new(KEY, AES.MODE_ECB)

    encryptedPart1 = bytes(packet[0:16])
    encryptedPart2 = bytes(packet[16:32])

    intermediatePart2 = cipher.decrypt(encryptedPart2)
    decrypedPart2 = bytes([e ^ i for e, i in zip(encryptedPart1, intermediatePart2)])
    decrypedPart1 = cipher.decrypt(encryptedPart1)

    return decrypedPart1 + decrypedPart2

def encryptPacket(packet):
    cipher = AES.new(KEY, AES.MODE_ECB)

    decryptedPart1 = bytes(packet[0:16])
    decryptedPart2 = bytes(packet[16:32])

    encryptedPart1 = cipher.encrypt(decryptedPart1)
    intermediatePart2 = bytes([e ^ i for e, i in zip(encryptedPart1, decryptedPart2)])
    encryptedPart2 = cipher.encrypt(intermediatePart2)

    return encryptedPart1 + encryptedPart2

def sendPacket(radio, address, packetId, payload):
    payload_size = len(payload)
    packed = struct.pack('BBBB28s', 1, 0, packetId, payload_size, payload)

    radio.stopListening()
    radio.openReadingPipe(1, SERVER_ADDRESS)
    radio.openWritingPipe(address)
    failed = radio.write(encryptPacket(bytes(packed)))
    radio.startListening()
    if failed:
        print("Failed sending packet (Not really something in the driver is broken)!")

def handle(radio, packet):
    counter, clientId, messageType, payloadSize = struct.unpack('BBBB', packet[:4])
    print("Recieving message type {0} with counter {1}".format(messageType, counter))
    if messageType == 0:
        time.sleep(0.02)
        address = list(struct.unpack('<BBBBBBBBBBBB20s', packet)[4:12][::-1][3:8])
        clientId = random.randint(1,254)
        print("Register {0} as {1}".format(bytes(address), clientId));
        sendPacket(radio, address, 1, bytes([ clientId ]))

if __name__ == "__main__":
    initializeGPIO()
    radio = initializeRadio()

    while True:
        while not radio.available([1]):
            time.sleep(1 / 100)

        encryptedPacket = []
        radio.read(encryptedPacket, 32)
        message = decryptPacket(encryptedPacket)
        handle(radio, bytes(message))