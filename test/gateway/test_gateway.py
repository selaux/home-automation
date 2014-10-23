import setup_test

setup_test.setup()

import unittest
import gateway
import random
from unittest.mock import MagicMock as Mock
from unittest.mock import patch


class TestGatewayMain(unittest.TestCase):
    @patch.multiple(gateway, asyncio=Mock(), atexit=Mock(), initialize_gpio=Mock(), Radio=Mock(), Router=Mock(),
                    poll=Mock())
    def test_main(self):
        loop_stub = Mock()
        router_stub = Mock()
        radio_stub = Mock()

        gateway.Router.return_value = router_stub
        gateway.Radio.return_value = radio_stub
        gateway.Radio.send_packet = {}
        gateway.asyncio.get_event_loop.return_value = loop_stub
        router_stub.connect_to_message_queue.return_value = 'Future'

        gateway.main()

        gateway.initialize_gpio.assert_called_once_with()
        gateway.Router.assert_called_once_with()
        gateway.Radio.assert_called_once_with()
        gateway.poll.assert_called_once_with(loop_stub, radio_stub, router_stub)
        loop_stub.run_until_complete.assert_called_once_with('Future')
        loop_stub.run_forever.assert_called_once_with()
        loop_stub.close.assert_called_once_with()


class TestGateway(unittest.TestCase):
    @patch.multiple(gateway, GPIO=Mock(), atexit=Mock())
    def test_initialize_gpio(self):
        gateway.initialize_gpio()
        gateway.GPIO.setmode.assert_called_once_with(gateway.GPIO.BCM)
        gateway.atexit.register.assert_called_once_with(gateway.GPIO.cleanup)

    @patch.multiple(gateway, partial=Mock(), asyncio=Mock())
    def test_poll_with_packet_available(self):
        expected_client_id = random.randint(1, 255)
        expected_message_id = random.randint(0, 255)
        expected_payload = bytes([1] * 8)

        loop = Mock()
        radio = Mock()
        router = Mock()

        gateway.partial.return_value = 'PartiallyAppliedFn'
        router.handle_packet.return_value = 'Future'
        radio.get_packet.return_value = (expected_client_id, expected_message_id, expected_payload)

        gateway.poll(loop, radio, router)

        router.handle_packet.assert_called_once_with(
            expected_client_id,
            expected_message_id,
            expected_payload,
            radio.send_packet)
        gateway.asyncio.async.assert_called_once_with('Future')
        loop.call_later.assert_called_once_with(0.04, 'PartiallyAppliedFn')

    @patch.multiple(gateway, partial=Mock(), asyncio=Mock())
    def test_poll_without_packet_available(self):
        loop = Mock()
        radio = Mock()
        router = Mock()

        radio.get_packet.return_value = False
        gateway.partial.return_value = 'PartiallyAppliedFn'

        gateway.poll(loop, radio, router)

        self.assertEqual(router.handle_packet.call_count, 0)
        loop.call_later.assert_called_once_with(0.04, 'PartiallyAppliedFn')

