from nrf24 import NRF24
from Crypto.Cipher import AES
import RPi.GPIO as GPIO
import time
import atexit

KEY = bytes([25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188 ])
SERVER_ADDRESS = [0xf0, 0xf0, 0xf0, 0xf0, 0xe1]

def initializeGPIO():
    GPIO.setmode(GPIO.BCM)

    @atexit.register
    def cleanupGPIO():
        print("Cleaning up GPIO before exit")
        GPIO.cleanup()
        if radio:
            radio.end()

def initializeRadio():
    radio = NRF24()
    radio.begin(0, 0, 25, 24)

    radio.setRetries(15, 15)
    radio.setPayloadSize(32)
    radio.setChannel(0x4c)
    radio.setDataRate(NRF24.BR_1MBPS)
    radio.setPALevel(NRF24.PA_MIN)
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

if __name__ == "__main__":
    initializeGPIO()
    radio = initializeRadio()

    while True:
        while not radio.available([1]):
            time.sleep(1 / 100)

        encryptedPacket = []
        radio.read(encryptedPacket, 32)
        message = decryptPacket(encryptedPacket)
        print("After")
        print (['{:02x}'.format(x) for x in message])