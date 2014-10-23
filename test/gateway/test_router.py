import setup_test

setup_test.setup()

import unittest
import router
import random
from asyncio import Future
from unittest.mock import MagicMock as Mock
from unittest.mock import patch

MOCK_SERVER_ID = [1, 2, 3, 4, 5, 6, 7, 8]


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.send_packet_stub = Mock()

    @patch.multiple(router, asynqp=Mock(), RABBITMQ_HOST='a', RABBITMQ_PORT=1, RABBITMQ_USERNAME='b',
                    RABBITMQ_PASSWORD='c', RABBITMQ_VIRTUAL_HOST='d')
    @setup_test.async_test
    def test_connect_to_message_queue(self):
        def create_future_with_result(result):
            future = Future()
            future.set_result(result)
            return future

        router_instance = router.Router()

        connection_stub = Mock()
        channel_stub = Mock()
        exchange_stub = Mock()
        queue_stub = Mock()

        router.asynqp.connect.return_value = create_future_with_result(connection_stub)
        connection_stub.open_channel.return_value = create_future_with_result(channel_stub)
        channel_stub.declare_exchange.return_value = create_future_with_result(exchange_stub)
        channel_stub.declare_queue.return_value = create_future_with_result(queue_stub)

        yield from router_instance.connect_to_message_queue()

        self.assertEqual(router_instance.connection, connection_stub)
        self.assertEqual(router_instance.channel, channel_stub)
        self.assertEqual(router_instance.exchange, exchange_stub)
        self.assertEqual(router_instance.queue, queue_stub)
        router.asynqp.connect.assert_called_once_with('a', 1, 'b', 'c', 'd')
        connection_stub.open_channel.assert_called_once_with()
        channel_stub.declare_exchange.assert_called_once('gateway.exchange', 'topic')
        channel_stub.declare_queue.assert_called_once('gateway.queue')


    @patch.multiple(router, SERVER_ID=MOCK_SERVER_ID)
    @setup_test.async_test
    def test_it_should_handle_a_registration_packet_and_send_back_an_acknowledgement(self):
        registration_packet_id = 0
        payload = bytes([1, 2, 3])
        expected_client_id = random.randint(1, 255)
        expected_packet_id = 1
        expected_response = bytes([expected_client_id]) + bytes(MOCK_SERVER_ID)
        router_instance = router.Router()

        yield from router_instance.handle_packet(expected_client_id,
                                                 registration_packet_id,
                                                 payload,
                                                 self.send_packet_stub)

        self.send_packet_stub.assert_called_once_with(expected_client_id, expected_packet_id, expected_response)



