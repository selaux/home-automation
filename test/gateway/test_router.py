import setup_test

setup_test.setup()

import unittest
import router
import random
from asyncio import Future
from unittest.mock import MagicMock as Mock
from unittest.mock import patch

MOCK_SERVER_ID = [1, 2, 3, 4, 5, 6, 7]
MOCK_SERVER_CHECKSUM = 121


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


    @patch.multiple(router, SERVER_ID=MOCK_SERVER_ID, SERVER_ID_CHECKSUM=MOCK_SERVER_CHECKSUM)
    @setup_test.async_test
    def test_it_should_handle_a_registration_packet_and_send_back_an_acknowledgement(self):
        registration_packet_id = 0
        payload = bytes([1, 2, 3])
        expected_client_id = random.randint(1, 255)
        expected_packet_id = 1
        expected_response = bytes([expected_client_id]) + bytes(MOCK_SERVER_ID) + bytes([MOCK_SERVER_CHECKSUM])
        router_instance = router.Router()
        router_instance.clear_subscription_channels = Mock()
        router_instance.set_send_packet(self.send_packet_stub)

        yield from router_instance.handle_packet(expected_client_id,
                                                 registration_packet_id,
                                                 payload)

        self.send_packet_stub.assert_called_once_with(expected_client_id, expected_packet_id, expected_response)
        router_instance.clear_subscription_channels.assert_called_once_with(expected_client_id)

    @setup_test.async_test
    def test_it_should_handle_a_subscription_packet(self):
        subscription_packet_id = 3
        expected_channel_id = random.randint(1, 255)
        expected_transform_id = random.randint(1, 255)
        expected_routing_key = 'test:routing:key'
        payload = bytes([expected_channel_id, expected_transform_id]) + bytes(expected_routing_key, encoding='ascii')
        expected_client_id = random.randint(1, 255)
        router_instance = router.Router()
        router_instance.add_subscription_channel = Mock()

        yield from router_instance.handle_packet(expected_client_id,
                                                 subscription_packet_id,
                                                 payload)

        router_instance.add_subscription_channel.assert_called_once_with(
            expected_client_id,
            expected_routing_key,
            expected_channel_id,
            expected_transform_id
        )

    @setup_test.async_test
    def test_add_subscription_channel_with_new_routing_key(self):
        expected_subscription_channels = {
            'foo.routing.key': [
                {'client_id': 1, 'channel_id': 2, 'transform_id': 3}
            ]
        }

        router_instance = router.Router()
        router_instance.queue = Mock()
        router_instance.exchange = Mock()
        yield from router_instance.add_subscription_channel(1, 'foo.routing.key', 2, 3)

        self.assertEqual(router_instance.subscription_channels, expected_subscription_channels)
        router_instance.queue.bind.assert_called_once_with(router_instance.exchange, 'foo.routing.key')

    @setup_test.async_test
    def test_add_subscription_channel_with_existing_routing_key(self):
        subscription_channels_before = {
            'foo.routing.key': [
                {'client_id': 0, 'channel_id': 0, 'transform_id': 0}
            ]
        }
        expected_subscription_channels = {
            'foo.routing.key': [
                {'client_id': 0, 'channel_id': 0, 'transform_id': 0},
                {'client_id': 1, 'channel_id': 2, 'transform_id': 3}
            ]
        }

        router_instance = router.Router()
        router_instance.queue = Mock()
        router_instance.exchange = Mock()
        router_instance.subscription_channels = subscription_channels_before
        yield from router_instance.add_subscription_channel(1, 'foo.routing.key', 2, 3)

        self.assertEqual(router_instance.subscription_channels, expected_subscription_channels)
        router_instance.queue.bind.assert_called_once_with(router_instance.exchange, 'foo.routing.key')

    def test_clear_subscription_channels(self):
        subscription_channels_before = {
            'foo.routing.key': [
                {'client_id': 0, 'channel_id': 0, 'transform_id': 0},
                {'client_id': 1, 'channel_id': 1, 'transform_id': 1}
            ],
            'bar.routing.key': [
                {'client_id': 1, 'channel_id': 1, 'transform_id': 1}
            ]
        }
        expected_subscription_channels = {
            'foo.routing.key': [
                {'client_id': 0, 'channel_id': 0, 'transform_id': 0}
            ],
            'bar.routing.key': []
        }

        router_instance = router.Router()
        router_instance.subscription_channels = subscription_channels_before
        router_instance.clear_subscription_channels(1)

        self.assertEqual(router_instance.subscription_channels, expected_subscription_channels)



