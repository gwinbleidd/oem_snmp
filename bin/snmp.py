#!/bin/python
# coding=utf-8
import os
import sys
import logging

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import send_trap

LOG_FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'application.log')
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

environment = dict(os.environ)

try:
    sequence_id = send_trap(environment)
    logging.debug(sequence_id)
except Exception as e:
    logging.error(e, exc_info=True)
    sys.exit(1)

print sequence_id