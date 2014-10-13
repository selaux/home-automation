import setup_test
setup_test.setup()

import unittest
import radio
import random
from mock import Mock, patch


class MockNRF24():
    BR_1MBPS = 1
    PA_HIGH = 2
    CRC_16 = 3

    def __init__(self):
        self.begin = Mock()
        self.setRetries = Mock()
        self.setPayloadSize = Mock()
        self.setChannel = Mock()
        self.setDataRate = Mock()
        self.setPALevel = Mock()
        self.setCRCLength = Mock()
        self.setAutoAck = Mock()
        self.enableAckPayload = Mock()
        self.openReadingPipe = Mock()
        self.openWritingPipe = Mock()
        self.startListening = Mock()
        self.printDetails = Mock()
        self.stopListening = Mock()
        self.write = Mock()
        self.read = Mock()
        self.available = Mock()
        self.writeAckPayload = Mock()

class TestRadio(unittest.TestCase):
    mock_server_address = [0x00, 0x00, 0x00, 0x00, 0x01]
    mock_client_address = [0x00, 0x00, 0x00, 0x00, 0x02]
    other_mock_client_address = [0x00, 0x00, 0x00, 0x00, 0x03]
    mock_server_id = [1, 2, 3, 4, 5, 6, 7, 8]

    def setUp(self):
        self.nrf_before = radio.NRF24
        self.server_address_before = radio.SERVER_ADDRESS
        self.server_id_before = radio.SERVER_ADDRESS
        radio.NRF24 = MockNRF24
        radio.SERVER_ADDRESS = self.mock_server_address
        radio.SERVER_ID = self.mock_server_id

    def tearDown(self):
        radio.NRF24 = self.nrf_before
        radio.SERVER_ADDRESS = self.server_address_before
        radio.SERVER_ID = self.server_id_before

    def test_init(self):
        radio_instance = radio.Radio()
        radio_instance.nrf24.begin.assert_called_once_with(0, 0, 25, 24)
        radio_instance.nrf24.setRetries.assert_called_once_with(15, 15)
        radio_instance.nrf24.setPayloadSize.assert_called_once_with(32)
        radio_instance.nrf24.setChannel.assert_called_once_with(0x4c)
        radio_instance.nrf24.setDataRate.assert_called_once_with(MockNRF24.BR_1MBPS)
        radio_instance.nrf24.setPALevel.assert_called_once_with(MockNRF24.PA_HIGH)
        radio_instance.nrf24.setCRCLength.assert_called_once_with(MockNRF24.CRC_16)
        radio_instance.nrf24.setAutoAck.assert_called_once_with(True)
        radio_instance.nrf24.enableAckPayload.assert_called_once_with()
        radio_instance.nrf24.openReadingPipe.assert_called_once_with(1, self.mock_server_address)
        radio_instance.nrf24.openWritingPipe.assert_called_once_with(self.mock_server_address)
        radio_instance.nrf24.startListening.assert_called_once_with()
        radio_instance.nrf24.printDetails.assert_called_once_with()

    @patch.object(radio, 'encrypt_packet')
    def test_send_packet_with_success(self, encrypt_mock):
        expected_packet = [1, 0, 5, 4, 1, 2, 3, 4]
        expected_packet = bytes(expected_packet)
        encrypted_packet = bytes([8] * 32)
        radio_instance = radio.Radio()
        radio_instance.client_ids_to_addresses[1] = self.mock_client_address
        radio_instance.nrf24.openReadingPipe.reset_mock()
        radio_instance.nrf24.openWritingPipe.reset_mock()
        radio_instance.nrf24.startListening.reset_mock()
        radio_instance.nrf24.write.return_value = True
        encrypt_mock.return_value = encrypted_packet

        success = radio_instance.send_packet(1, 5, bytes([1, 2, 3, 4]))

        self.assertEqual(len(encrypt_mock.call_args[0][0]), 32)
        self.assertEqual(encrypt_mock.call_args[0][0][:len(expected_packet)], expected_packet)
        radio_instance.nrf24.stopListening.assert_called_once_with()
        radio_instance.nrf24.openReadingPipe.assert_called_once_with(1, self.mock_server_address)
        radio_instance.nrf24.openWritingPipe.assert_called_once_with(self.mock_client_address)
        radio_instance.nrf24.write.assert_called_once_with(encrypted_packet)
        radio_instance.nrf24.startListening.assert_called_once()

        self.assertEqual(success, True)

    def test_send_packet_with_error(self):
        radio_instance = radio.Radio()
        radio_instance.client_ids_to_addresses[1] = self.mock_client_address
        radio_instance.nrf24.write.return_value = False

        success = radio_instance.send_packet(1, 5, bytes([1, 2, 3, 4]))

        self.assertEqual(success, False)

    def test_is_packet_available_with_a_packet_available(self):
        radio_instance = radio.Radio()
        radio_instance.nrf24.available.return_value = True

        self.assertEqual(radio_instance.is_packet_available(), True)

    def test_is_packet_available_with_no_packet_available(self):
        radio_instance = radio.Radio()
        radio_instance.nrf24.available.return_value = False

        self.assertEqual(radio_instance.is_packet_available(), False)
        radio_instance.nrf24.writeAckPayload.assert_called_once_with(1, bytes(self.mock_server_id), 8)

    @patch.object(radio, 'decrypt_packet')
    def test_get_packet(self, decrypt_mock):
        radio_instance = radio.Radio()
        expected_client_id = 100
        expected_message_id = 101
        expected_payload = [1, 2, 3, 4]
        decrypted_packet = [39, expected_client_id, expected_message_id, len(expected_payload)]
        decrypted_packet.extend(expected_payload)
        decrypted_packet.extend([16])
        decrypt_mock.return_value = bytes(decrypted_packet)

        client_id, message_id, payload = radio_instance.get_packet()

        self.assertEqual(client_id, expected_client_id)
        self.assertEqual(message_id, expected_message_id)
        self.assertEqual(payload, bytes(expected_payload))
        decrypt_mock.assert_called_once_with([])

    @patch.object(radio, 'decrypt_packet')
    def test_get_packet_with_registration_message(self, decrypt_mock):
        address = self.mock_client_address
        radio_instance = radio.Radio()
        radio_instance.get_client_id = Mock()
        expected_counter = 10000
        expected_client_id = 100
        radio_instance.get_client_id.return_value = expected_client_id
        registration_message_id = 0
        decrypted_packet = [39, expected_client_id, registration_message_id, len(address)]
        decrypted_packet.extend(address[::-1])
        decrypted_packet.extend([16])
        decrypt_mock.return_value = bytes(decrypted_packet)

        client_id, message_id, payload = radio_instance.get_packet()

        self.assertEqual(client_id, expected_client_id)
        self.assertEqual(message_id, registration_message_id)
        self.assertEqual(payload, bytes(address[::-1]))
        self.assertEqual(radio_instance.client_ids_to_addresses[expected_client_id], address)
        self.assertEqual(radio_instance.client_ids_to_counters[expected_client_id], expected_counter)

    def test_get_client_id_with_new_client_address(self):
        radio_instance = radio.Radio()
        number_already_registered = random.randint(0, 255)

        for i in range(number_already_registered):
            radio_instance.client_ids_to_addresses[i+1] = self.other_mock_client_address

        self.assertEqual(radio_instance.get_client_id(self.mock_client_address), number_already_registered+1)

    def test_get_client_id_with_existing_client_address(self):
        radio_instance = radio.Radio()
        expected_client_id = random.randint(1, 255)

        radio_instance.client_ids_to_addresses[expected_client_id] = self.mock_client_address

        self.assertEqual(radio_instance.get_client_id(self.mock_client_address), expected_client_id)

    def test_get_client_address_without_remaining_client_ids(self):
        radio_instance = radio.Radio()
        number_already_registered = 254

        for i in range(number_already_registered):
            radio_instance.client_ids_to_addresses[i+1] = self.other_mock_client_address

        self.assertEqual(radio_instance.get_client_id(self.mock_client_address), False)



