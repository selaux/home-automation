import setup_test

setup_test.setup()

import unittest
import router
import random
import transforms
from asyncio import Future
from unittest.mock import MagicMock as Mock
from unittest.mock import patch

MOCK_SERVER_ID = [1, 2, 3, 4, 5, 6, 7]
MOCK_SERVER_CHECKSUM = 121


class TestRouter(unittest.TestCase):
    def setUp(self):
        self.send_packet_stub = Mock()

    def test_transform_registration(self):
        expected_transforms = {
            0: transforms.SwitchTransform
        }
        router_instance = router.Router()
        self.assertEqual(router_instance.transforms, expected_transforms)

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
        router_instance.clear_publish_channels = Mock()
        router_instance.set_send_packet(self.send_packet_stub)

        yield from router_instance.handle_packet(expected_client_id,
                                                 registration_packet_id,
                                                 payload)

        self.send_packet_stub.assert_called_once_with(expected_client_id, expected_packet_id, expected_response)
        router_instance.clear_subscription_channels.assert_called_once_with(expected_client_id)
        router_instance.clear_publish_channels.assert_called_once_with(expected_client_id)

    @setup_test.async_test
    def test_it_should_handle_a_subscription_channel_packet(self):
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
    def test_it_should_handle_a_publish_channel_packet(self):
        subscription_packet_id = 2
        expected_channel_id = random.randint(1, 255)
        expected_transform_id = random.randint(1, 255)
        expected_routing_key = 'test:routing:key'
        payload = bytes([expected_channel_id, expected_transform_id]) + bytes(expected_routing_key, encoding='ascii')
        expected_client_id = random.randint(1, 255)
        router_instance = router.Router()
        router_instance.add_publish_channel = Mock()

        yield from router_instance.handle_packet(expected_client_id,
                                                 subscription_packet_id,
                                                 payload)

        router_instance.add_publish_channel.assert_called_once_with(
            expected_client_id,
            expected_routing_key,
            expected_channel_id,
            expected_transform_id
        )

    @setup_test.async_test
    def test_it_should_handle_a_publish_packet(self):
        publish_packet_id = 4
        client_id = random.randint(1, 255)
        channel_id = random.randint(1, 255)
        transform_id = random.randint(1, 255)
        expected_routing_key = 'test:routing:key'
        expected_message = {'foo': 'bar'}
        payload = bytes([channel_id]) + bytes([1, 2, 3, 4])
        transform_mock = Mock()
        transform_mock.to_message.return_value = expected_message

        router_instance = router.Router()
        router_instance.exchange = Mock()
        router_instance.transforms[transform_id] = transform_mock
        router_instance.publish_channels = {
            client_id: [
                {'channel_id': channel_id, 'transform_id': transform_id, 'routing_key': expected_routing_key}
            ]
        }

        yield from router_instance.handle_packet(client_id,
                                                 publish_packet_id,
                                                 payload)

        router_instance.exchange.publish.assert_called_once()
        message = router_instance.exchange.publish.call_args[0][0]
        routing_key = router_instance.exchange.publish.call_args[0][1]
        self.assertEqual(message.json(), expected_message)
        self.assertEqual(routing_key, expected_routing_key)

    @setup_test.async_test
    def test_it_should_handle_a_publish_packet_with_unknown_client_id(self):
        publish_packet_id = 4
        client_id = 99
        channel_id = random.randint(1, 255)
        payload = bytes([channel_id]) + bytes([1, 2, 3, 4])

        router_instance = router.Router()

        with self.assertLogs(router.LOGGER) as log_messages:
            yield from router_instance.handle_packet(client_id,
                                                     publish_packet_id,
                                                     payload)

        log_messages = log_messages.output
        self.assertIn('WARNING:router:Client 99 tried to publish, but has no channels set up', log_messages)

    @setup_test.async_test
    def test_it_should_handle_a_publish_packet_with_unknown_channel_id(self):
        publish_packet_id = 4
        client_id = 99
        channel_id = 100
        payload = bytes([channel_id]) + bytes([1, 2, 3, 4])

        router_instance = router.Router()
        router_instance.publish_channels = {
            client_id: []
        }

        with self.assertLogs(router.LOGGER) as log_messages:
            yield from router_instance.handle_packet(client_id,
                                                     publish_packet_id,
                                                     payload)

        log_messages = log_messages.output
        self.assertIn('WARNING:router:Client 99 tried to publish message with unknown channel 100', log_messages)

    def test_add_publish_channel_with_new_client_id(self):
        expected_publish_channels = {
            1: [
                {'routing_key': 'foo.routing.key', 'channel_id': 2, 'transform_id': 3}
            ]
        }

        router_instance = router.Router()
        router_instance.transforms[3] = Mock()
        router_instance.add_publish_channel(1, 'foo.routing.key', 2, 3)

        self.assertEqual(router_instance.publish_channels, expected_publish_channels)

    def test_add_publish_channel_with_existing_client_id(self):
        publish_channels_before = {
            1: [
                {'routing_key': 'foo.routing.key', 'channel_id': 0, 'transform_id': 0}
            ]
        }
        expected_publish_channels = {
            1: [
                {'routing_key': 'foo.routing.key', 'channel_id': 0, 'transform_id': 0},
                {'routing_key': 'bar.routing.key', 'channel_id': 2, 'transform_id': 3}
            ]
        }

        router_instance = router.Router()
        router_instance.transforms[3] = Mock()
        router_instance.publish_channels = publish_channels_before
        router_instance.add_publish_channel(1, 'bar.routing.key', 2, 3)

        self.assertEqual(router_instance.publish_channels, expected_publish_channels)

    def test_add_publish_channel_with_unknown_transform_id(self):
        client_id = 99
        channel_id = 1
        transform_id = 100

        router_instance = router.Router()

        with self.assertLogs(router.LOGGER) as log_messages:
            router_instance.add_publish_channel(client_id, 'bar.routing.key', channel_id, transform_id)

        log_messages = log_messages.output
        self.assertIn(
            'WARNING:router:Client 99 tried to register pub-channel 1 with unknown transform 100',
            log_messages
        )

    def test_clear_publish_channels(self):
        publish_channels_before = {
            1: [
                {'routing_key': 'foo.routing.key', 'channel_id': 0, 'transform_id': 0},
                {'routing_key': 'bar.routing.key', 'channel_id': 1, 'transform_id': 1}
            ],
            2: [
                {'routing_key': 'baz.routing.key', 'channel_id': 1, 'transform_id': 1}
            ]
        }
        expected_subscription_channels = {
            2: [
                {'routing_key': 'baz.routing.key', 'channel_id': 1, 'transform_id': 1}
            ]
        }

        router_instance = router.Router()
        router_instance.publish_channels = publish_channels_before
        router_instance.clear_publish_channels(1)

        self.assertEqual(router_instance.publish_channels, expected_subscription_channels)

    @setup_test.async_test
    def test_add_subscription_channel_with_new_routing_key(self):
        expected_subscription_channels = {
            'foo.routing.key': [
                {'client_id': 1, 'channel_id': 2, 'transform_id': 3}
            ]
        }

        router_instance = router.Router()
        router_instance.transforms[3] = Mock()
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
        router_instance.transforms[3] = Mock()
        router_instance.queue = Mock()
        router_instance.exchange = Mock()
        router_instance.subscription_channels = subscription_channels_before
        yield from router_instance.add_subscription_channel(1, 'foo.routing.key', 2, 3)

        self.assertEqual(router_instance.subscription_channels, expected_subscription_channels)
        router_instance.queue.bind.assert_called_once_with(router_instance.exchange, 'foo.routing.key')

    @setup_test.async_test
    def test_add_subscription_channel_with_unknown_transform_id(self):
        client_id = 99
        channel_id = 1
        transform_id = 100

        router_instance = router.Router()

        with self.assertLogs(router.LOGGER) as log_messages:
            yield from router_instance.add_subscription_channel(client_id, 'bar.routing.key', channel_id, transform_id)

        log_messages = log_messages.output
        self.assertIn(
            'WARNING:router:Client 99 tried to register sub-channel 1 with unknown transform 100',
            log_messages
        )

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



