#!/bin/python
# coding=utf-8

import logging
from logging.handlers import TimedRotatingFileHandler
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import *


def main():
    # Основная процедура
    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)
    handler = TimedRotatingFileHandler(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'test.log'),
        when="D",
        interval=1)

    formatter = logging.Formatter("%(asctime)s - %(process)d - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    environment_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'environment11.json')

    with open(environment_file, 'r') as json_file:
        environment = json.load(json_file)

    try:
        sequence_id = send_trap_for_oem11(environment)
        logging.info(sequence_id)
        print sequence_id
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()
