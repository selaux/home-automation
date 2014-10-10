import setup_test
setup_test.setup()

import unittest
import crypto
import random


class CryptoTestCase(unittest.TestCase):
    def setUp(self):
        self.psk_before = crypto.PRESHARED_KEY
        crypto.PRESHARED_KEY = bytes([1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1])

    def tearDown(self):
        crypto.PRESHARED_KEY = self.psk_before

class TestEncryptPacket(CryptoTestCase):
    def test_encrypt_should_encrypt_a_packet(self):
        packet = [1] * 32
        expected = [94, 119, 229, 159, 143, 133, 148, 52, 137, 162, 65, 73, 199, 95, 78, 201, 140, 217, 26, 172, 142,
                    219, 245, 20, 152, 62, 105, 149, 241, 5, 26, 22]

        self.assertEqual(crypto.encrypt_packet(bytes(packet)), bytes(expected))

    def test_the_two_blocks_of_the_encrypted_packet_should_change_if_one_of_the_first_bits_changes(self):
        packet = [random.randint(0, 255) for dummy in range(32)]
        encrypted_unchanged_packet = crypto.encrypt_packet(bytes(packet))

        packet[1] = packet[1]+1 if packet[1] < 255 else 0
        encrypted_changed_packet = crypto.encrypt_packet(bytes(packet))

        self.assertNotEqual(encrypted_changed_packet[:16], encrypted_unchanged_packet[:16])
        self.assertNotEqual(encrypted_changed_packet[16:], encrypted_unchanged_packet[16:])

    def test_encrypt_decrypt_cycle_should_work(self):
        packet = bytes([random.randint(0, 255) for dummy in range(32)])
        cycled_packet = crypto.decrypt_packet(crypto.encrypt_packet(packet))

        self.assertEqual(packet, cycled_packet)


class TestDecryptPacket(CryptoTestCase):
    def test_decrypt_should_decrypt_a_packet(self):
        packet = [1] * 32
        expected = [188, 110, 43, 175, 35, 202, 30, 102, 170, 215, 179, 149, 193, 214, 166, 10, 189, 111, 42, 174, 34,
                    203, 31, 103, 171, 214, 178, 148, 192, 215, 167, 11]

        self.assertEqual(crypto.decrypt_packet(bytes(packet)), bytes(expected))

    def test_decrypt_encrypt_cycle_should_work(self):
        packet = bytes([random.randint(0, 255) for dummy in range(32)])
        cycled_packet = crypto.encrypt_packet(crypto.decrypt_packet(packet))

        self.assertEqual(packet, cycled_packet)
