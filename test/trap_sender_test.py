#!/bin/python
# coding=utf-8

import logging
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import *


def main():
    # Основная процедура
    log_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'test.log')
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format="%(asctime)s - %(process)d - %(levelname)s - %(message)s")

    environment_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'environment.json')

    with open(environment_file, 'r') as json_file:
        environment = json.load(json_file)

    try:
        sequence_id = send_trap(environment)
        logging.info(sequence_id)
        print sequence_id
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()