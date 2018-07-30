#!/bin/python
# coding=utf-8

import logging
import sys
import os
import json
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import *

LOG_FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'application.log')
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

environment_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'environment.json')

with open(environment_file, 'r') as json_file:
    environment = json.load(json_file)

try:
    sequence_id = send_trap(environment)
    logging.info(sequence_id)
    print sequence_id
except Exception as e:
    logging.error(e, exc_info=True)
    sys.exit(1)
