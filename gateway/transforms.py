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
