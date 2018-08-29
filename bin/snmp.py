#!/bin/python
# coding=utf-8
import os
import sys
import getopt
import logging
import time
import json
from logging.handlers import TimedRotatingFileHandler

# Импортируем все, что понаписали в папке lib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import send_trap_for_oem13, send_trap_for_oem11


def usage():
    print 'Usage: snmp.py -v [11|13]'
    sys.exit(2)


def main(argv):
    # Парсим параметры вызова
    # Должен быть обязательно указан параметр -v с номером
    # версии ОЕМ(11 для 11g, 13 - для 13c), для которой вызывается скрипт
    version = ''
    try:
        opts, args = getopt.getopt(argv, "hv:")

        for opt, arg in opts:
            if opt == '-h':
                print 'snmp.py -v [11|13]'
                sys.exit()
            elif opt == '-v':
                if arg in ('11', '13'):
                    version = arg
                else:
                    usage()
            else:
                usage()
    except getopt.GetoptError:
        usage()
    # Основная процедура
    # Определяем логгер
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # попытка определить хэндлер с ротацией логов по времени, но не сработало так как задумывалось
    # поэтому был настроен logrotate примерно следующего содержания:
    # <путь к папке установки скрипта>/log/application.log    {
    #     rotate 3
    #     missingok
    #     notifempty
    #     compress
    #     daily
    #     create 0640
    #     postrotate
    #         tar -zcf <путь к папке установки скрипта>/log/backup/logs_`date + "%Y%m%d"`.tar.gz\
    #           $(find <путь к папке установки скрипта>/log/*.json -type f -mtime -1 -daystart) --remove-files
    #     endscript
    # }
    handler = TimedRotatingFileHandler(
        os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'application.log'),
        when="D",
        interval=1)
    # определяем формат записи в лог
    formatter = logging.Formatter("%(asctime)s - %(process)d - %(levelname)s - %(message)s")
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    # загружаем переменные окружения. ОЕМ при вызове скрипта передает через них параметры события,
    # из-за которого этот вызов происходит
    environment = dict(os.environ)
    if version == '13':
        try:
            # Вызываем отправку трапа
            # Должен вернуть ИД события и его статус, чтобы показать его в ОЕМе
            sequence_id = send_trap_for_oem13(environment)
            logging.info(sequence_id)
            print sequence_id
        except Exception as e:
            logging.info(json.dumps(environment, indent=3, sort_keys=True))
            logging.error(e, exc_info=True)
    elif version == '11':
        try:
            # Вызываем отправку трапа
            # Должен вернуть ИД события и его статус, чтобы показать его в ОЕМе
            sequence_id = send_trap_for_oem11(environment)
            logging.info(sequence_id)
            print sequence_id
        except Exception as e:
            logging.info(json.dumps(environment, indent=3, sort_keys=True))
            logging.error(e, exc_info=True)


if __name__ == "__main__":
    main(sys.argv[1:])
