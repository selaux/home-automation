"""Crypto functions used in the gateway"""

from Crypto.Cipher import AES
from settings import PRESHARED_KEY

def decrypt_packet(packet):
    """Decrypt packet for transmission over rf24"""
    cipher = AES.new(PRESHARED_KEY, AES.MODE_ECB)

    encrypted_part1 = bytes(packet[0:16])
    encrypted_part2 = bytes(packet[16:32])

    intermediate_part2 = cipher.decrypt(encrypted_part2)
    decrypted_part2 = bytes([e ^ i for e, i in zip(encrypted_part1, intermediate_part2)])
    decrypted_part1 = cipher.decrypt(encrypted_part1)

    return decrypted_part1 + decrypted_part2


def encrypt_packet(packet):
    """Encrypt packet for transmission over rf24"""
    cipher = AES.new(PRESHARED_KEY, AES.MODE_ECB)

    decrypted_part1 = bytes(packet[0:16])
    decrypted_part2 = bytes(packet[16:32])

    encrypted_part1 = cipher.encrypt(decrypted_part1)
    intermediate_part2 = bytes([e ^ i for e, i in zip(encrypted_part1, decrypted_part2)])
    encrypted_part2 = cipher.encrypt(intermediate_part2)

    return encrypted_part1 + encrypted_part2
