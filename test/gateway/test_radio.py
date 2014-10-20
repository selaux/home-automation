import setup_test
setup_test.setup()

import unittest
import radio
import random
import logging
from unittest.mock import MagicMock as Mock
from unittest.mock import patch


class MockNRF24():
    BR_250KBPS = 1
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

MOCK_SERVER_ADDRESS = [0x00, 0x00, 0x00, 0x00, 0x01]
MOCK_CLIENT_ADDRESS = [0x00, 0x00, 0x00, 0x00, 0x02]
OTHER_MOCK_CLIENT_ADDRESS = [0x00, 0x00, 0x00, 0x00, 0x03]
MOCK_SERVER_ID = [1, 2, 3, 4, 5, 6, 7, 8]


class TestRadio(unittest.TestCase):
    def setUp(self):
        logger = logging.getLogger()
        for han in logger.handlers[:]:
            logger.removeHandler(han)
        for fil in logger.filters[:]:
            logger.removeFilter(fil)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_init(self):
        logging.basicConfig(level=logging.INFO)
        radio_instance = radio.Radio()
        radio_instance.nrf24.begin.assert_called_once_with(0, 0, 25, 24)
        radio_instance.nrf24.setRetries.assert_called_once_with(15, 15)
        radio_instance.nrf24.setPayloadSize.assert_called_once_with(32)
        radio_instance.nrf24.setChannel.assert_called_once_with(0x4c)
        radio_instance.nrf24.setDataRate.assert_called_once_with(MockNRF24.BR_250KBPS)
        radio_instance.nrf24.setPALevel.assert_called_once_with(MockNRF24.PA_HIGH)
        radio_instance.nrf24.setCRCLength.assert_called_once_with(MockNRF24.CRC_16)
        radio_instance.nrf24.setAutoAck.assert_called_once_with(True)
        radio_instance.nrf24.enableAckPayload.assert_called_once_with()
        radio_instance.nrf24.openReadingPipe.assert_called_once_with(1, MOCK_SERVER_ADDRESS)
        radio_instance.nrf24.openWritingPipe.assert_called_once_with(MOCK_SERVER_ADDRESS)
        radio_instance.nrf24.startListening.assert_called_once_with()
        radio_instance.nrf24.printDetails.assert_called_once_with()

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_init_with_higher_loglevel(self):
        logging.basicConfig(level=logging.WARN)
        radio_instance = radio.Radio()
        self.assertFalse(radio_instance.nrf24.printDetails.called)


    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    @patch.object(radio, 'encrypt_packet')
    def test_send_packet_with_success(self, encrypt_mock):
        expected_packet = [39, 0, 5, 4, 1, 2, 3, 4]
        expected_packet = bytes(expected_packet)
        encrypted_packet = bytes([8] * 32)
        radio_instance = radio.Radio()
        radio_instance.clients = [{
            'client_id': 1,
            'address': MOCK_CLIENT_ADDRESS,
            'server_counter': 10000
        }]
        radio_instance.nrf24.openReadingPipe.reset_mock()
        radio_instance.nrf24.openWritingPipe.reset_mock()
        radio_instance.nrf24.startListening.reset_mock()
        radio_instance.nrf24.write.return_value = True
        encrypt_mock.return_value = encrypted_packet

        success = radio_instance.send_packet(1, 5, bytes([1, 2, 3, 4]))

        self.assertEqual(len(encrypt_mock.call_args[0][0]), 32)
        self.assertEqual(encrypt_mock.call_args[0][0][:len(expected_packet)], expected_packet)
        self.assertEqual(encrypt_mock.call_args[0][0][-1], 16)
        radio_instance.nrf24.stopListening.assert_called_once_with()
        radio_instance.nrf24.openReadingPipe.assert_called_once_with(1, MOCK_SERVER_ADDRESS)
        radio_instance.nrf24.openWritingPipe.assert_called_once_with(MOCK_CLIENT_ADDRESS)
        radio_instance.nrf24.write.assert_called_once_with(encrypted_packet)
        radio_instance.nrf24.startListening.assert_called_once()

        self.assertEqual(success, True)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_send_packet_with_error(self):
        radio_instance = radio.Radio()
        radio_instance.clients = [{
            'client_id': 1,
            'address': MOCK_CLIENT_ADDRESS,
            'server_counter': 10000
        }]
        radio_instance.nrf24.write.return_value = False

        success = radio_instance.send_packet(1, 5, bytes([1, 2, 3, 4]))

        self.assertEqual(success, False)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def setup_for_test_get_packet(self, decrypt_mock):
        radio_instance = radio.Radio()
        radio_instance.nrf24.available.return_value = True
        radio_instance.has_client_id = Mock(return_value=True)
        radio_instance.is_counter_is_in_expected_range = Mock(return_value=True)
        client_id = 100
        message_id = 101
        payload = [1, 2, 3, 4]
        counter_byte_1 = 16
        counter_byte_2 = 39
        decrypted_packet = [counter_byte_2, client_id, message_id, len(payload)]
        decrypted_packet.extend(payload)
        decrypted_packet.extend([counter_byte_1])
        decrypt_mock.return_value = bytes(decrypted_packet)
        return radio_instance

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    @patch.object(radio, 'decrypt_packet')
    def test_get_packet_with_a_packet_available(self, decrypt_mock):
        radio_instance = self.setup_for_test_get_packet(decrypt_mock)
        radio_instance.clients.append({'client_id': 100, 'client_counter': 9999})

        client_id, message_id, payload = radio_instance.get_packet()

        self.assertEqual(client_id, 100)
        self.assertEqual(message_id, 101)
        self.assertEqual(payload, bytes([1, 2, 3, 4]))
        self.assertEqual(radio_instance.clients[0]['client_counter'], 10000)
        decrypt_mock.assert_called_once_with([])
        radio_instance.has_client_id.assert_called_once_with(100)
        radio_instance.is_counter_is_in_expected_range.assert_called_once_with(100, 10000)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    @patch.object(radio, 'decrypt_packet')
    def test_get_packet_with_a_packet_that_has_a_unknown_client_id(self, decrypt_mock):
        radio_instance = self.setup_for_test_get_packet(decrypt_mock)
        radio_instance.has_client_id.return_value = False

        self.assertEqual(radio_instance.get_packet(), False)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    @patch.object(radio, 'decrypt_packet')
    def test_get_packet_with_a_packet_that_has_a_counter_that_is_not_in_the_expected_range(self, decrypt_mock):
        radio_instance = self.setup_for_test_get_packet(decrypt_mock)
        radio_instance.is_counter_is_in_expected_range.return_value = False

        self.assertEqual(radio_instance.get_packet(), False)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    @patch.object(radio, 'decrypt_packet')
    def test_get_packet_without_a_packet_available(self, decrypt_mock):
        radio_instance = self.setup_for_test_get_packet(decrypt_mock)
        radio_instance.nrf24.available.return_value = False

        self.assertEqual(radio_instance.get_packet(), False)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    @patch.object(radio, 'decrypt_packet')
    def test_get_packet_with_registration_message(self, decrypt_mock):
        address = MOCK_CLIENT_ADDRESS
        expected_client_id = 100
        registration_message_id = 0
        radio_instance = self.setup_for_test_get_packet(decrypt_mock)
        radio_instance.get_client_id = Mock(return_value=expected_client_id)
        decrypted_packet = [39, expected_client_id, registration_message_id, len(address)]
        decrypted_packet.extend(address[::-1])
        decrypted_packet.extend([16])
        decrypt_mock.return_value = bytes(decrypted_packet)

        client_id, message_id, payload = radio_instance.get_packet()

        self.assertEqual(client_id, expected_client_id)
        self.assertEqual(message_id, registration_message_id)
        self.assertEqual(payload, bytes(address[::-1]))
        self.assertEqual(radio_instance.clients[0]['client_id'], expected_client_id)
        self.assertEqual(radio_instance.clients[0]['client_counter'], 10000)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_is_counter_in_expected_range(self):
        client_id = 100
        current_client_counter = 65533
        test_cases = [
            (100, False),
            (65533, False),
            (65534, True),
            (65535, True),
            (0, True),
            (7, True),
            (8, False),
            (10, False),
        ]

        radio_instance = radio.Radio()
        radio_instance.clients.append({'client_id': client_id, 'client_counter': current_client_counter})
        for counter, expected in test_cases:
            with self.subTest(counter=counter, expected=expected):
                self.assertEqual(radio_instance.is_counter_is_in_expected_range(client_id, counter), expected)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_has_client_id(self):
        client_id = 100
        test_cases = [
            ([{'client_id':100}], True),
            ([{'client_id':101}], False),
            ([], False),
        ]
        radio_instance = radio.Radio()
        for clients, expected in test_cases:
            with self.subTest(clients=clients, expected=expected):
                radio_instance.clients = clients
                self.assertEqual(radio_instance.has_client_id(client_id), expected)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_get_client_id_with_new_client_address(self):
        radio_instance = radio.Radio()
        number_already_registered = random.randint(0, 255)

        for i in range(number_already_registered):
            radio_instance.clients.append({'client_id': i+1, 'address': OTHER_MOCK_CLIENT_ADDRESS})

        self.assertEqual(radio_instance.get_client_id(MOCK_CLIENT_ADDRESS), number_already_registered+1)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_get_client_id_with_existing_client_address(self):
        radio_instance = radio.Radio()
        expected_client_id = random.randint(1, 255)

        radio_instance.clients.append({'client_id': expected_client_id, 'address': MOCK_CLIENT_ADDRESS})

        self.assertEqual(radio_instance.get_client_id(MOCK_CLIENT_ADDRESS), expected_client_id)

    @patch.multiple(radio, NRF24=MockNRF24, SERVER_ADDRESS=MOCK_SERVER_ADDRESS)
    def test_get_client_address_without_remaining_client_ids(self):
        radio_instance = radio.Radio()
        number_already_registered = 254

        for i in range(number_already_registered):
            radio_instance.clients.append({'client_id': i+1, 'address': OTHER_MOCK_CLIENT_ADDRESS})

        self.assertEqual(radio_instance.get_client_id(MOCK_CLIENT_ADDRESS), False)



