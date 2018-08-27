# coding=utf-8

import subprocess
import os
import json
import re
import datetime
import hashlib
import logging


# класс-обертка для утилиты Emcli
# нужен для выполнения команд по общению с ОЕМ из Python-скрипта
class Emcli(object):
    def __init__(self):
        # конструктор
        # ищем файл .object.json. Если таковой есть, восстанавливаем объект из него
        if os.path.isfile(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                                       '.object.json')):
            self.__from_json()
        else:
            # если не нашли - начинаем с чистого листа
            self.__get_config()
            # выставляем параметры атрибутов объекта
            self.configured = self.__get_configured()
            self.last_configured_check = datetime.datetime.now()
            self.logged_in = self.__get_logged_in()
            self.last_logged_in_check = datetime.datetime.now()

        # если не нашли бинарник emcli - "Шеф, все пропало..."
        if self.__check_binary() is None:
            raise Exception('EMCLI binary not found')

    def __check_binary(self):
        # проверяем наличие бинарника
        def is_exe(fpath):
            # удостоверимся, что предложенное существует и является исполняемым модулем
            return os.path.isfile(fpath) and os.access(fpath, os.X_OK)

        file_path, file_name = os.path.split(self.config['bin'])

        if file_path:
            # если указан путь к файлу, проверяем на существование
            if is_exe(self.config['bin']):
                return self.config['bin']
        else:
            # если путь не указан, проверяем PATH
            for path in os.environ["PATH"].split(os.pathsep):
                exe_file = os.path.join(path, self.config['bin'])
                if is_exe(exe_file):
                    return exe_file

        # если ничего не помогло, возвращаем None
        return None

    def execute(self, *args):
        # процедура выполнения команды через emcli
        # имя команды и ее параметры передаются через args
        logging.debug('Executing %s' % ', '.join(args))
        # собираем параметры для запуска
        params = list(args)
        # в начало списка добавляем бинарник emcli...
        params.insert(0, self.config['bin'].encode('ascii'))
        # ...и подсовываем это все subprocess для выполнения
        process = subprocess.Popen(params, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
        # возвращаем то, что нагенерил subprocess
        return process.stdout.readlines()

    def __get_configured(self):
        # проверяем, сконфигурирован для emcli
        # выполняем комаду status
        output = self.execute('status')
        for line in output:
            # если результат матчится с регулярным выражением, то все в порядке
            if re.match('^Status\s+: Configured$', line):
                logging.debug('Emcli configured')
                return True

        # если нет - все плохо
        logging.debug('Emcli not configured')
        return False

    def __get_logged_in(self):
        # логинимся в ОЕМ
        try:
            # грузим конфиг .emcli.json из файла в формате JSON
            # на все файлы в папке .secure должны быть установлены права 600, на саму папку - 700 для пущей безопасности
            # в нем обязательно должны быть 2 секции:
            # 1. name - имя пользователя ОЕМ, который имеет право пользоваться Emcli
            # 2. password - его пароль. Лучше сделать отдельного пользователя, но можно ходить и sysman'ом
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                                   '.emcli.json'), 'r') as json_file:
                self.user = json.load(json_file)
        except Exception:
            raise Exception('Error loading user.json')

        # выполняем комаду login через Emcli, параметры - имя пользователя и пароль
        output = self.execute('login', '-username=%s' % self.user['name'], '-password=%s' % self.user['password'])
        self.user = None
        for line in output:
            # если результат матчится с регулярным выражением, то все в порядке
            if re.match('Login successful', line) or re.match('Error: Already logged in', line):
                logging.debug('Emcli logged in')
                return True

        # если нет - все плохо
        logging.debug('Emcli not logged in')
        return False

    def logout(self):
        # отключаемся от ОЕМ
        # выполняем комаду logout через Emcli
        output = self.execute('logout')
        for line in output:
            # если результат матчится с регулярным выражением, то все в порядке
            if re.match('Logout successful', line) or re.match('Error: Already logged out', line):
                logging.debug('Emcli logged out')
                self.logged_in = False

    def __to_json(self):
        # сереализуем объект в JSON
        dump = {'config': self.config,  # сохраняем конфиг
                'configured': {'state': str(self.configured),
                               'last_check': self.last_configured_check.strftime('%Y-%m-%d %H:%M:%S')},  # сохраняем статус configured
                'logged_in': {'state': str(self.logged_in),
                              'last_check': self.last_logged_in_check.strftime('%Y-%m-%d %H:%M:%S')}}    # сохраняем статус logged_in

        # сохраняем в файл
        with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                               '.object.json'), 'w') as json_file:
            json.dump(dump, json_file, indent=4, sort_keys=True)

        # и обеспечиваем безопасность - выставляем права 600 на этот файл
        os.chmod(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                              '.object.json'), 0o600)

        logging.debug('Emcli object stored to json')

    def __get_config(self):
        # грузим конфиг из файла формата JSON
        # в нем обязательно должно быть 2 секции:
        # 1. bin - путь к бинарнику emcli
        # 2. url - URL сервера OEM
        try:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                                   'emcli.json'), 'r') as json_file:
                self.config = json.load(json_file)
                # обновляем чек-сумму конфига для отслеживания факта его изменения
                self.config.update({'config_checksum': hashlib.sha256(
                    os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                                 'emcli.json')).hexdigest()})
        except Exception:
            raise Exception('Error loading config.json')

    def __from_json(self):
        # загружаем объект из сохраненного ранее файла .secure/.object.json
        try:
            with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                                   '.object.json'), 'r') as object_file:
                dump = json.load(object_file)
        except Exception:
            raise Exception('Error loading object file')

        # проверяем чек-сумму конфига emcli
        config_checksum = hashlib.sha256(
            os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                         'emcli.json')).hexdigest()

        # если совпадает - не будем перечитывать конфиг, возмем сохраненный
        if config_checksum == dump['config']['config_checksum']:
            self.config = dump['config']
        else:
            # если нет - считываем заново
            self.__get_config()

        # восстанавливаем метки времени последних проверок logged_in и configured
        last_logged_in_check = datetime.datetime.strptime(dump['logged_in']['last_check'], '%Y-%m-%d %H:%M:%S')
        last_configured_check = datetime.datetime.strptime(dump['configured']['last_check'], '%Y-%m-%d %H:%M:%S')

        now = datetime.datetime.now()
        if last_logged_in_check < now + datetime.timedelta(minutes=-45):
            # если с момента последнего логина прошло больше 45 минут
            # повторяем эту операцию
            self.logged_in = self.__get_logged_in()
            self.last_logged_in_check = now
        else:
            # если нет - обновляем состояние и метки времени
            self.logged_in = True if dump['logged_in']['state'] == 'True' else False
            self.last_logged_in_check = last_logged_in_check
            # если вообще не залогинены - исправляем этот досадный недостаток
            if not self.logged_in:
                self.logged_in = self.__get_logged_in()
                self.last_logged_in_check = now

        if last_configured_check < now + datetime.timedelta(days=-1):
            # если с момента последней проверки сконфигурированности emcli прошло больше 1 дня
            # повторяем эту операцию
            self.configured = self.__get_configured()
            self.last_configured_check = now
        else:
            # если нет - обновляем состояние и метки времени
            self.configured = True if dump['configured']['state'] == 'True' else False
            self.last_configured_check = last_configured_check

    def get_event_id(self, *args):
        # функция возвращает ID события, с которым связана проблема или инцидент, из ОЕМ
        # она необходима для того, чтобы на нашей стороне связать событие и породивший/порожденный инцидент/проблему
        result = []
        # возможно выполнение в двух вариантах - без проверки по полю Severity
        if len(args) == 1:
            # запрос к БД ОЕМ
            query = 'SELECT DISTINCT E.EVENT_SEQ_ID FROM SYSMAN.MGMT$EVENTS E WHERE INCIDENT_ID = HEXTORAW(\'%s\')' % \
                    args[0]
            # выполняем его через emcli
            process = self.execute('list', '-sql=%s' % query, '-format=name:csv')

            for line in process:
                # разбираемся с результатом
                # ID должно быть строкой 32 символа в 16-ричном формате
                # если есть такое в выводе комады - возвращаем
                match_object = re.search('([ABCDEF0-9]{32})', line)
                if match_object:
                    result.append(match_object.group(1))

            if len(result) != 0:
                logging.debug('Event ID found, %s' % ', '.join(result))
                return result
            else:
                logging.debug('Event ID not found')
                return None
        # и с ней
        elif len(args) == 2:
            query = 'SELECT DISTINCT E.EVENT_SEQ_ID FROM SYSMAN.MGMT$EVENTS E WHERE INCIDENT_ID = HEXTORAW (\'%s\') AND SEVERITY = \'%s\'' % (
                args[0], args[1])
            process = self.execute('list', '-sql=%s' % query, '-format=name:csv')

            for line in process:
                match_object = re.search('([ABCDEF0-9]{32})', line)
                if match_object:
                    result.append(match_object.group(1))

            if len(result) != 0:
                logging.debug('Event ID found, %s' % ', '.join(result))
                return result
            else:
                logging.debug('Event ID not found')
                return None

        return None

    def check_message_sent(self, *args):
        # функция проверяет, было ли сообщение о событии из ОЕМ отправлено
        # она необходима для того, чтобы не отправлять сообщений и по событию,
        # и по порожденному/породившему инциденту/проблеме
        query = """SELECT COUNT (*)\
                   FROM   SYSMAN.MGMT$EVENTS  E\
                   JOIN SYSMAN.MGMT$ALERT_HISTORY A ON E.EVENT_ID = A.EVENT_INSTANCE_ID\
                   JOIN SYSMAN.MGMT$ALERT_NOTIF_LOG ANL\
                   ON A.VIOLATION_GUID = ANL.SOURCE_OBJ_GUID\
                   WHERE E.INCIDENT_ID = HEXTORAW (\'%s\') AND E.SEVERITY = \'%s\'""" % (args[0], args[1])
        process = self.execute('list', '-sql=%s' % query, '-format=name:csv')

        for line in process:
            match_object = re.search('(\d+)', line)
            if match_object:
                if match_object.group(1) != '0':
                    logging.debug('Message for ID %s found' % ', '.join(args))
                    return True
        logging.debug('Message for ID %s not found' % ', '.join(args))
        return False

    def __del__(self):
        # деструктор для объекта
        # если со времени последней проверки залогированности прошло 40 минут - разлогиниваемся
        if self.last_logged_in_check < datetime.datetime.now() + datetime.timedelta(minutes=-40):
            self.logout()
        # сериализуем объект в JSON и выставляем права на файл
        self.__to_json()
        os.chmod(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure',
                              '.object.json'), 0o600)
