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
