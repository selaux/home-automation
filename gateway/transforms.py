# pylint: disable=no-init

"""All transforms from packets to dict and vice versa"""

from struct import pack, unpack

class SwitchTransform:
    """Transform for a switch type client which just has a on/off state"""
    @staticmethod
    def to_message(payload):
        """Use first byte of payload as boolean"""
        status = unpack('?', payload[:1])[0]
        return {
            'status': status
        }

    @staticmethod
    def to_packet(obj):
        """Use first byte of payload as the status"""
        return pack('?', obj['status'])

class TemperatureTransform:
    """Transform for a temperature type client which has temperature, humidity and dewpoint"""
    @staticmethod
    def to_message(payload):
        """Use first byte of payload as boolean"""
        temperature, humidity = unpack('ff', payload[:8])
        return {
            'temperature': temperature,
            'humidity': humidity
        }

    @staticmethod
    def to_packet(obj):
        """Use first byte of payload as the status"""
        return pack('ff', obj['temperature'], obj['humidity'])
