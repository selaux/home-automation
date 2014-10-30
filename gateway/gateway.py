"""Should eventually become the gateway between rabbitmq and the sensors/actuators listening on rf24 radio"""

import atexit
import asyncio
import os
import logging
try:
    import RPi.GPIO as GPIO
except(RuntimeError, ImportError) as error:
    if 'TEST_ENV' in os.environ:
        LOGGER = logging.getLogger(__name__)
        LOGGER.warn("Assuming test-environment.")
        class GPIO:
            """This will be stubbed in tests"""
            def __init__(self):
                pass
    else:
        raise error
from functools import partial

from radio import Radio
from router import Router

def initialize_gpio():
    """Initialize GPIO (handles pin numbering and cleanup)"""
    GPIO.setmode(GPIO.BCM)
    atexit.register(GPIO.cleanup)

def poll(loop, radio, router):
    """Poll for radio messages, decrypt them and pass them to the handler"""
    packet = radio.get_packet()
    if packet:
        client_id, message_id, payload = packet
        asyncio.async(router.handle_packet(client_id, message_id, payload))

    loop.call_later(0.04, partial(poll, loop, radio, router))

def main():
    """Runs the gateway"""
    loop = asyncio.get_event_loop()

    router = Router()
    loop.run_until_complete(router.connect_to_message_queue())

    initialize_gpio()
    radio = Radio()

    router.set_send_packet(radio.send_packet)

    poll(loop, radio, router)
    try:
        loop.run_forever()
    finally:
        loop.close()

if __name__ == "__main__":
    main()
