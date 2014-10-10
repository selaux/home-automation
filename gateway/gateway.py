"""Should eventually become the gateway between rabbitmq and the sensors/actuators listening on rf24 radio"""

import atexit
import asyncio
import RPi.GPIO as GPIO

from radio import Radio
from router import Router

def initialize_gpio():
    """Initialize GPIO (handles pin numbering and cleanup)"""
    GPIO.setmode(GPIO.BCM)

    @atexit.register
    def dummy_cleanup_gpio():
        """Clean up GPIO pins"""
        print("Cleaning up GPIO before exit")
        GPIO.cleanup()

@asyncio.coroutine
def run():
    """Poll for radio messages, decrypt them and pass them to the handler"""
    initialize_gpio()
    radio = Radio()
    router = Router(radio.send_packet)

    while True:
        if not radio.is_packet_available():
            yield from asyncio.sleep(0.04)
        else:
            client_id, message_id, payload = radio.get_packet()
            asyncio.async(router.handle_packet(client_id, message_id, payload))

def main():
    """Runs the gateway"""
    loop = asyncio.get_event_loop()
    try:
        loop.run_until_complete(run())
    finally:
        loop.close()

if __name__ == "__main__":
    main()
