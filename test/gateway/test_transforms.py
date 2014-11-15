import setup_test

setup_test.setup()

import unittest
import transforms


class TestSwitchTransform(unittest.TestCase):
    def test_to_message_with_true(self):
        result = transforms.SwitchTransform.to_message(bytes([1]))
        expected = {'status': True}
        self.assertEqual(result, expected)

    def test_to_message_with_false(self):
        result = transforms.SwitchTransform.to_message(bytes([0]))
        expected = {'status': False}
        self.assertEqual(result, expected)

    def test_to_packet_with_true(self):
        result = transforms.SwitchTransform.to_packet({'status': True})
        expected = bytes([1])
        self.assertEqual(result, expected)

    def test_to_packet_with_false(self):
        result = transforms.SwitchTransform.to_packet({'status': False})
        expected = bytes([0])
        self.assertEqual(result, expected)


class TestTemperatureTransform(unittest.TestCase):
    def test_to_message(self):
        result = transforms.TemperatureTransform.to_message(bytes([0, 0, 188, 65, 0, 0, 113, 66]))
        expected = {'temperature': 23.5, 'humidity': 60.25}
        self.assertEqual(result, expected)

    def test_to_packet(self):
        result = transforms.TemperatureTransform.to_packet({'temperature': 23.5, 'humidity': 60.25})
        expected = bytes([0, 0, 188, 65, 0, 0, 113, 66])
        self.assertEqual(result, expected)
