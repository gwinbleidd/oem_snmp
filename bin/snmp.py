#!/bin/python
# coding=utf-8
import os
import sys
import logging
import time


sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import send_trap


def main():
    # Основная процедура
    log_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'application.log')
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format="%(asctime)s - %(process)d - %(levelname)s - %(message)s")

    environment = dict(os.environ)
    try:
        # Вызываем отправку трапа
        # Должен вернуть ИД события, чтобы показать его в ОЕМе
        sequence_id = send_trap(environment)
        logging.info(sequence_id)
        print sequence_id
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()
