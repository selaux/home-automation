import setup_test
setup_test.setup()

import unittest
import router
import random
from mock import Mock

class TestRouter(unittest.TestCase):
    mock_server_id = [1, 2, 3, 4, 5, 6, 7, 8]

    def setUp(self):
        self.send_packet_stub = Mock()
        self.server_id_before = router.SERVER_ID
        router.SERVER_ID = self.mock_server_id

    def tearDown(self):
        router.SERVER_ID = self.server_id_before

    @setup_test.async_test
    def test_it_should_handle_a_registration_packet_and_send_back_an_acknowledgement(self):
        registration_packet_id = 0
        payload = bytes([1, 2, 3])
        expected_client_id = random.randint(1, 255)
        expected_packet_id = 1
        expected_response = bytes([expected_client_id]) + bytes(self.mock_server_id)
        router_instance = router.Router()

        yield from router_instance.handle_packet(expected_client_id,
                                                 registration_packet_id,
                                                 payload,
                                                 self.send_packet_stub)

        self.send_packet_stub.assert_called_once_with(expected_client_id, expected_packet_id, expected_response)



