"""All settings for the message queue gateway"""

import random
import logging

random.seed()

PRESHARED_KEY = bytes([25, 123, 90, 174, 198, 145, 40, 33, 98, 90, 90, 111, 78, 65, 184, 188])

SERVER_ADDRESS = [0xf0, 0xf0, 0xf0, 0xf0, 0xe1]
SERVER_ID = [random.randint(0, 255) for dummy in range(7)]

logging.basicConfig(level=logging.INFO, format='%(asctime)s;%(name)s;%(levelname)s;%(message)s')

RABBITMQ_HOST = 'localhost'
RABBITMQ_PORT = 5672
RABBITMQ_USERNAME = 'gateway'
RABBITMQ_PASSWORD = 'gateway'
RABBITMQ_VIRTUAL_HOST = '/home-automation'
