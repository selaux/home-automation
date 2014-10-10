"""Should eventually become the gateway between rabbitmq and the sensors/actuators listening on rf24 radio"""

import atexit
import asyncio
import os
try:
    import RPi.GPIO as GPIO
except(RuntimeError, ImportError) as error:
    if 'TEST_ENV' in os.environ:
        print("Assuming test-environment")
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
    if radio.is_packet_available():
        client_id, message_id, payload = radio.get_packet()
        asyncio.async(router.handle_packet(client_id, message_id, payload, radio.send_packet))

    loop.call_later(0.04, partial(poll, loop, radio, router))

def main():
    """Runs the gateway"""
    initialize_gpio()
    radio = Radio()
    router = Router()

    loop = asyncio.get_event_loop()
    poll(loop, radio, router)
    try:
        loop.run_forever()
    finally:
        loop.close()

if __name__ == "__main__":
    main()
