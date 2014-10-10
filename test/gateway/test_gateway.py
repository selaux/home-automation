import setup_test
setup_test.setup()

import unittest
import gateway
import random
from mock import Mock

class TestGatewayMain(unittest.TestCase):
    radio = 'radio'
    router = 'router'

    def setUp(self):
        self.asyncio_before = gateway.asyncio
        self.initialize_gpio_before = gateway.initialize_gpio
        self.radio_before = gateway.Radio
        self.router_before = gateway.Router
        self.poll_before = gateway.poll
        gateway.asyncio = Mock()
        gateway.atexit = Mock()
        gateway.initialize_gpio = Mock()
        gateway.Radio = Mock()
        gateway.Radio.return_value = self.radio
        gateway.Radio.send_packet = {}
        gateway.Router = Mock()
        gateway.Router.return_value = self.router
        gateway.poll = Mock()
        self.loop_stub = Mock()
        gateway.asyncio.get_event_loop.return_value = self.loop_stub

    def tearDown(self):
        gateway.asyncio = self.asyncio_before
        gateway.initialize_gpio = self.initialize_gpio_before
        gateway.Radio = self.radio_before
        gateway.Router = self.router_before
        gateway.poll = self.poll_before

    def test_main(self):
        gateway.main()

        gateway.initialize_gpio.assert_called_once_with()
        gateway.Radio.assert_called_once_with()
        gateway.Router.assert_called_once_with()
        gateway.poll.assert_called_once_with(self.loop_stub, self.radio, self.router)
        self.loop_stub.run_forever.assert_called_once_with()
        self.loop_stub.close.assert_called_once_with()

class TestGateway(unittest.TestCase):
    def setUp(self):
        self.gpio_before = gateway.GPIO
        self.atexit_before = gateway.atexit
        self.partial_before = gateway.partial
        self.asyncio_before = gateway.asyncio
        gateway.GPIO = Mock()
        gateway.atexit = Mock()
        gateway.asyncio = Mock()
        gateway.partial = Mock()

    def tearDown(self):
        gateway.GPIO = self.gpio_before
        gateway.atexit = self.atexit_before
        gateway.partial = self.partial_before
        gateway.asyncio = self.asyncio_before

    def test_initialize_gpio(self):
        gateway.initialize_gpio()
        gateway.GPIO.setmode.assert_called_once_with(gateway.GPIO.BCM)
        gateway.atexit.register.assert_called_once_with(gateway.GPIO.cleanup)

    def test_poll_with_packet_available(self):
        expected_client_id = random.randint(1, 255)
        expected_message_id = random.randint(0, 255)
        expected_payload = bytes([1] * 8)

        loop = Mock()
        radio = Mock()
        router = Mock()

        gateway.partial.return_value = 'PartiallyAppliedFn'
        router.handle_packet.return_value = 'Future'
        radio.is_packet_available.return_value = True
        radio.get_packet.return_value = (expected_client_id, expected_message_id, expected_payload)

        gateway.poll(loop, radio, router)

        router.handle_packet.assert_called_once_with(
            expected_client_id,
            expected_message_id,
            expected_payload,
            radio.send_packet)
        gateway.asyncio.async.assert_called_once_with('Future')
        loop.call_later.assert_called_once_with(0.04, 'PartiallyAppliedFn')


    def test_poll_without_packet_available(self):
        pass