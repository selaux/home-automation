"""Crypto functions used in the gateway"""

from Crypto.Cipher import AES
from settings import PRESHARED_KEY

def decrypt_packet(packet):
    """Decrypt packet for transmission over rf24"""
    cipher = AES.new(PRESHARED_KEY, AES.MODE_ECB)

    encrypted_part1 = bytes(packet[0:16])
    encrypted_part2 = bytes(packet[16:32])

    intermediate_part1 = cipher.decrypt(encrypted_part1)
    decrypted_part1 = bytes([e ^ i for e, i in zip(encrypted_part2, intermediate_part1)])
    decrypted_part2 = cipher.decrypt(encrypted_part2)

    return decrypted_part1 + decrypted_part2


def encrypt_packet(packet):
    """Encrypt packet for transmission over rf24"""
    cipher = AES.new(PRESHARED_KEY, AES.MODE_ECB)

    decrypted_part1 = bytes(packet[0:16])
    decrypted_part2 = bytes(packet[16:32])

    encrypted_part2 = cipher.encrypt(decrypted_part2)
    intermediate_part1 = bytes([e ^ i for e, i in zip(encrypted_part2, decrypted_part1)])
    encrypted_part1 = cipher.encrypt(intermediate_part1)

    return encrypted_part1 + encrypted_part2

def xor_checksum(array):
    """Calculate XOR Checksum for an array of bytes"""
    result = 0
    for index, value in enumerate(bytes(array)):
        result = result & 0xFF ^ (value << index) & 0xFF
    return result

