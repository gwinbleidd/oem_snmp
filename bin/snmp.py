#!/bin/python
# coding=utf-8
import os
import sys
import logging
import time
from logging.handlers import TimedRotatingFileHandler

# Импортируем все, что понаписали в папке lib
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from trap_sender import send_trap


def main():
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
    try:
        # Вызываем отправку трапа
        # Должен вернуть ИД события и его статус, чтобы показать его в ОЕМе
        sequence_id = send_trap(environment)
        logging.info(sequence_id)
        print sequence_id
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()
