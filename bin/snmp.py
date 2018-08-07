#!/bin/python
# coding=utf-8
import os
import sys
import logging
import time
from logging.handlers import TimedRotatingFileHandler


sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import send_trap


def main():
    # Основная процедура
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    handler = TimedRotatingFileHandler(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'application.log'),
        when="D",
        interval=1)

    formatter = logging.Formatter("%(asctime)s - %(process)d - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

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
