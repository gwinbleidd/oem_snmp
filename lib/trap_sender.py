# coding=utf-8

from pysnmp.hlapi import *
from pyzabbix import ZabbixMetric, ZabbixSender
import socket
import re
import os
import json
import time
import logging
import psutil

from event_logger import log_event
from emcli import Emcli
from zabbix_api import *


def send_zabbix_trap(oms_event):
    config = get_config()
    zabbix = config['zabbix']
    # Все поля трапа OEM, которые мы будем передавать, получены из MIBа omstrap.v1
    trap_parameters = config['trap_parameters']
    # Собираем Zabbix трап
    # Чтобы не было одновременной отправки нескольких сообщений
    # Добавляем функционал файла блокировок таким образом, чтобы
    # все наши процессы по отправке заббикс трапов шли по очереди
    # Нужно запомнить ИД процесса
    pid = os.getpid()

    # Разбираемся с лок-файлом
    # Лок-файл лежит в папке .secure
    lock_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.lock')
    if os.path.isfile(lock_file):
        # Если такой файл есть, дописываем в него ИД процесса
        with open(lock_file, 'a+') as lock:
            lock.write(str(pid) + '\n')
    else:
        # Если нет - создаем и записываем
        with open(lock_file, 'w+') as lock:
            lock.write(str(pid) + '\n')

    logging.info('Sent PID %d to lock file' % pid)

    # Собираем переменные трапа
    trap_variables = dict()

    for trap_variable in trap_parameters:
        if trap_variable in oms_event:
            trap_variables.update({trap_variable: oms_event[trap_variable]})

    # Формируем метрику
    try:
        # В качестве метрики берем тот же набор параметров,
        # что и для SNMP трапа, но сваливаем его в json
        # и в таком виде отправляем в Заббикс
        m = ZabbixMetric(oms_event['oraEMNGEventHostName'], 'data',
                         json.dumps(trap_variables, indent=3, sort_keys=True))
        zbx = ZabbixSender(zabbix['host'])

        # Проверяем, что наша очередь работать
        # Для этого ИД нашего процесса должен стоять первым в списке
        processes = list()
        counter = 0
        with open(lock_file, 'r') as lock:
            for line in lock:
                if line.replace('\n', '').strip() != '' and psutil.pid_exists(
                        int(line.replace('\n', '').strip())):
                    processes.append(line.replace('\n', '').strip())

        # Если не первый - ждем своей очереди
        if processes[0] != str(pid):
            logging.info('First PID is %s. It\'s not equal ours, sleeping' % processes[0])
            logging.info('Process queue is [%s]. ' % ', '.join(processes))

        while processes[0] != str(pid) and counter < 5:
            # Ждем 1 секунду
            # Потому, что Заббикс не может разделить два пришедших события
            # если у них совпадает метка времени
            # А метка времени у него берется с точностью до секунды
            time.sleep(1)
            # Но не более 5 раз
            counter += 1
            processes = list()
            with open(lock_file, 'r') as lock:
                for line in lock:
                    if line.replace('\n', '').strip() != '' and psutil.pid_exists(
                            int(line.replace('\n', '').strip())):
                        processes.append(line.replace('\n', '').strip())
            logging.info('Process queue is [%s]. ' % ', '.join(processes))

        # Наша очередь, поехали
        if counter == 5:
            logging.info('Enough waiting, running')
        else:
            logging.info('First PID is ours, running')

        # Отправляем
        response = zbx.send([m])

        # Проверяем ответ
        # Наша отправка не должна зафейлиться, но должна быть обработана
        if response is not None:
            if response.failed == 1:
                oms_event.update({'TrapState': oms_event['TrapState'] + ', exception zabbix'})
            elif response.processed == 1:
                oms_event.update({'TrapState': oms_event['TrapState'] + ', send zabbix'})
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e
    finally:
        # В конце концов, поработал - прибери за собой
        # Удаляем из лок-файла свой ИД
        # По логике, он должен быть первым в файле, но чем черт не шутит
        # Поэтому считываем весь файл, а потом перезаписываем его всем его содержимым кроме строки с нашим ИД
        processes = list()
        with open(lock_file, 'r') as lock:
            for line in lock:
                if line.replace('\n', '').strip() != '' and psutil.pid_exists(
                        int(line.replace('\n', '').strip())):
                    processes.append(line.replace('\n', '').strip())

        with open(lock_file, 'w') as lock:
            for line in processes:
                if line != str(pid):
                    lock.write(line + '\n')

        processes.remove(str(pid))

        logging.info('Final process queue is [%s]. ' % ', '.join(processes))

        if os.path.getsize(lock_file) == 0:
            os.remove(lock_file)


def send_snmp_trap(oms_event):
    # Собираем SNMP трап
    # Для этого нужен MIB (Management Information Base)
    # # Есть проблема, Питон не хочет подхватывать напрямую MIB-файл из OMS,
    # # который лежит $OMS_HOME/network/doc/omstrap.v1. Кроме того, в дефолтном файле
    # # слишком много ненужной (устаревшей) информации. Поэтому мы удалили все OIDы oraEM4Alert,
    # # кроме тех которые необходимы для копиляции. После этого скомпилировали полученный MIB
    # # скриптом mibdump.py, который идет в поставке с пакетом pysmi, который ставиться pip'ом
    # # и положил полученный *.py файл в /usr/lib/python2.7/site-packages/pysnmp/smi/mibs с правами 644

    config = get_config()
    hostname = config['hostname']
    zabbix = config['zabbix']
    # Все поля трапа OEM, которые мы будем передавать, получены из MIBа omstrap.v1
    trap_parameters = config['trap_parameters']

    address = socket.gethostbyname(hostname)

    # Собираем переменные трапа
    trap_variables = [(ObjectIdentity('DISMAN-EVENT-MIB', 'sysUpTimeInstance'), TimeTicks(int(time.time()))),
                      (ObjectIdentity('SNMP-COMMUNITY-MIB', 'snmpTrapAddress', 0), address)]

    for trap_variable in trap_parameters:
        trap_variables.append((ObjectIdentity('ORACLE-ENTERPRISE-MANAGER-4-MIB', trap_variable),
                               oms_event[trap_variable].replace('"',
                                                                "'") if trap_variable in oms_event else ''))

    # Посылаем трап
    try:
        logging.debug('Trying to send SNMP trap')
        error_indication, error_status, error_index, var_binds = next(
            sendNotification(
                SnmpEngine(),
                CommunityData('public', mpModel=0),
                UdpTransportTarget((zabbix['host'], zabbix['port'])),
                ContextData(),
                'trap',
                NotificationType(
                    ObjectIdentity('ORACLE-ENTERPRISE-MANAGER-4-MIB', 'oraEMNGEvent')
                ).addVarBinds(*trap_variables)
            )
        )

        if error_indication:
            logging.debug('SNMP exception')
            oms_event.update({'TrapState': 'exception'})
            log_event(oms_event_to_log=oms_event)
            raise Exception(error_indication)
        else:
            logging.debug('SNMP sent')
            oms_event.update({'TrapState': 'send snmp'})
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e


def filter_trap(**kwargs):
    # Фильтр входящих сообщений
    # На вход функции подается некие параметры трапа
    # На основе конфигурационного файла filter.json
    # проверяется, пропускать ли этот трап или нет
    # На настоящий момент проверяются только поля MESSAGE и EVENT_NAME
    # В конфигурационном фале записи состоят из ключа - имени поля, которое проверяется
    # и значения - массива регулярных выражений, которыми это поле проверяется.
    # При совпадении хотя бы с одним из них функция возвращает признак
    # неоходимости фильтрации сообщения
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                           'filter.json'), 'r') as json_file:
        filters = json.load(json_file)
        for filter_key, filter_value in filters.iteritems():
            if filter_key in kwargs and kwargs[filter_key] is not None:
                for value in filter_value:
                    regexp = re.compile(value.encode('ascii'))
                    match_object = regexp.search(kwargs[filter_key])
                    if match_object:
                        logging.debug('Matched filter expression %s' % value.encode('ascii'))
                        return True

    return False


def get_config():
    # Загружаем конфиг
    # в конфиге должны быть 4 секции:
    # 1. trap_to_environment_variables - маппинг переменных трапа в переменные окружения
    # 2. trap_parameters - параметры трапа, которые будут отправлены
    # 3. hostname - имя хоста ОЕМ
    # 4. zabbix - параметры хоста самого Заббикса или одного из его прокси,
    #    к которому подключены все(!) хосты, которые мониторятся в ОЕМ
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                           'snmp.json'), 'r') as json_file:
        return json.load(json_file)


def send_trap_for_oem11(environment):
    # Выставляем признак неотправки трапа
    do_not_send_trap = False
    reason = 'trap not skipped'

    config = get_config()

    # Маппинг переменных окружения в переменные трапа в соответствии с MIBом
    # # Переменные перечислены в соответсвии с главой
    # # "3.10.2 Passing Event, Incident, Problem Information to an OS Command or Script"
    # # документа Oracle® Enterprise Manager Cloud Control Administrator's Guide
    # # Если зачению переменной трапа может соответствовать несколько переменных окружения
    # # в зависимости от события, которое обрабатывается, такие переменные представлены
    # # в виде словаря, в которых ключ соответствует переменной ISSUE_TYPE - тип события,
    # # значение - переменной, которую нужно подставить
    trap_to_environment_variables = config['11']['trap_to_environment_variables']

    # На вход получаем параметры окружения в виде словаря, которые создает OMS при вызове скрипта
    # Собираем только те параметры, которые укладываются в стандартный MIB omstrap.v1 Oracle OEM 13c
    # Кроме того, сохраняем в oms_event['oraEMNGEnvironment'] все переменные окружения, мало ли что-то упустили
    oms_event = {'oraEMNGEnvironment': environment,
                 'oraEMNGEventSequenceId': 'null'}

    for trap_variable, os_variable in trap_to_environment_variables.iteritems():
        oms_event.update({trap_variable: environment[os_variable] if os_variable in environment else ''})

    # Нужно подправить некоторые элементы
    # Во-первых:
    #  подрезаем длину сообщения и URL события до 255 символов, чтобы влезало в трап
    #  по просьбе дежурных, удаляем хвост .severstal.severstalgroup.com из имени цели
    #  заменяем значение oraEMNGAssocIncidentAcked на Yes/No, как в варианте для 13с вместо 1/0
    oms_event.update({'oraEMNGEventMessage': oms_event['oraEMNGEventMessage'][:255],
                      'oraEMNGEventTargetName': oms_event['oraEMNGEventTargetName'].replace(
                          '.severstal.severstalgroup.com', ''),
                      'oraEMNGAssocIncidentAcked': 'No' if oms_event['oraEMNGAssocIncidentAcked'] == '0' else 'Yes'})

    # Проверяем, если пришла закрывашка, а открывающего события в Заббиксе нет, отправлять не будем
    try:
        if oms_event['oraEMNGEventSeverity'] == 'Clear' or oms_event['oraEMNGAssocIncidentAcked'] == 'Yes':
            request = get_event_by_id(oms_event['oraEMNGEventSequenceId'])
            if request is None or len(request) == 0:
                do_not_send_trap = True
                reason = 'Clear\\acknowledge message came, Open message doesn\'t exists'
        else:
            logging.debug('Opening message exists in Zabbix')
            do_not_send_trap = do_not_send_trap
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e

    # Проверяем, если пришла закрывашка, будем закрывать через API, не будем отправлять
    try:
        if oms_event['oraEMNGEventSeverity'] == 'Clear' or oms_event['oraEMNGAssocIncidentAcked'] == 'Yes':
            logging.debug('Trying to acknowledge event to close it by API method')
            result = acknowledge_event_by_id(oms_event['oraEMNGEventSequenceId'])
            if result is not None and len(result) != 0:
                if 'TrapState' not in oms_event:
                    oms_event.update({'TrapState': 'closed by api'})
                do_not_send_trap = True
                reason = 'closed by API'
            else:
                do_not_send_trap = do_not_send_trap
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e

    # Проверяем, нет ли случайно в Заббиксе события с таким же текстом
    # отображаемого на экране
    # Если есть - отсылать его не нужно
    try:
        if check_if_message_exists(
                '%s %s %s: %s Acknowledge=%s' % (oms_event['oraEMNGEventSequenceId'],
                                                 oms_event['oraEMNGEventSeverity'],
                                                 oms_event['oraEMNGEventTargetName'],
                                                 oms_event['oraEMNGEventMessage'],
                                                 oms_event['oraEMNGAssocIncidentAcked'])) and not (
                oms_event['oraEMNGEventSeverity'] == 'Clear' or oms_event['oraEMNGAssocIncidentAcked'] == 'Yes'):
            logging.debug('Message exists in Zabbix, skipping')
            do_not_send_trap = True
            reason = 'Repeated message'
        else:
            logging.debug('Message do not exists in Zabbix')
            do_not_send_trap = do_not_send_trap
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e

    # Если не стоит признак не посылать трап,
    if not do_not_send_trap:
        # Проверяем, нужно ли фильтровать трап
        # Если да - отсылать не будем
        if not filter_trap(message=oms_event['oraEMNGEventMessage'] if 'oraEMNGEventMessage' in oms_event else None,
                           event_name=oms_event['oraEMNGEventName'] if 'oraEMNGEventName' in oms_event else None):
            logging.debug('Message not filtered')
            # Для начала закроем событие в заббиксе с таким же ИД
            # если таковой имеется
            # но не трогаем закрывашки
            try:
                if not oms_event['oraEMNGEventSeverity'] == 'Clear' and not oms_event[
                                                                                'oraEMNGAssocIncidentAcked'] == 'Yes':
                    logging.debug('Trying to acknowledge event in Zabbix')
                    acknowledge_event_by_id(oms_event['oraEMNGEventSequenceId'])
            except Exception as e:
                log_event(oms_event_to_log=oms_event)
                raise e

            # Отправляем SNMPv1 трап
            send_snmp_trap(oms_event)

            # Отправляем Zabbix трап
            # В дальнейшем от одного из этих методов можно будет отказаться
            # Пока делаем так
            send_zabbix_trap(oms_event)
        else:
            logging.debug('Event filtered')
            if 'TrapState' not in oms_event:
                oms_event.update({'TrapState': 'filtered'})
    else:
        logging.debug('Event skipped')
        if 'TrapState' not in oms_event:
            oms_event.update({'TrapState': 'skipped, reason: %s' % reason})

    log_event(oms_event_to_log=oms_event)

    # Возвращаем полученный SequenceID
    return '%s: %s' % (oms_event['oraEMNGEventSequenceId'], oms_event['TrapState'])


def send_trap_for_oem13(environment):
    # Выставляем признак неотправки трапа
    do_not_send_trap = False
    reason = 'trap not skipped'

    config = get_config()

    # Маппинг переменных окружения в переменные трапа в соответствии с MIBом
    # # Переменные перечислены в соответсвии с главой
    # # "3.10.2 Passing Event, Incident, Problem Information to an OS Command or Script"
    # # документа Oracle® Enterprise Manager Cloud Control Administrator's Guide
    # # Если зачению переменной трапа может соответствовать несколько переменных окружения
    # # в зависимости от события, которое обрабатывается, такие переменные представлены
    # # в виде словаря, в которых ключ соответствует переменной ISSUE_TYPE - тип события,
    # # значение - переменной, которую нужно подставить
    trap_to_environment_variables = config['13']['trap_to_environment_variables']

    # На вход получаем параметры окружения в виде словаря, которые создает OMS при вызове скрипта
    # Собираем только те параметры, которые укладываются в стандартный MIB omstrap.v1 Oracle OEM 13c
    # Кроме того, сохраняем в oms_event['oraEMNGEnvironment'] все переменные окружения, мало ли что-то упустили
    oms_event = {'oraEMNGEnvironment': environment,
                 'oraEMNGEventSequenceId': 'null'}

    for trap_variable, os_variable in trap_to_environment_variables.iteritems():
        if type(os_variable) is unicode:
            oms_event.update({trap_variable: environment[os_variable] if os_variable in environment else ''})
        elif type(os_variable) is dict:
            issue_type = environment['ISSUE_TYPE']
            oms_event.update({trap_variable: environment[os_variable[issue_type]] if (issue_type in os_variable and
                                                                                      os_variable[
                                                                                          issue_type] in environment) else ''})

    # Нужно подправить некоторые элементы
    # Во-первых:
    #  подрезаем длину сообщения и URL события до 255 символов, чтобы влезало в трап
    #  по просьбе дежурных, удаляем хвост .severstal.severstalgroup.com из имени цели
    oms_event.update({'oraEMNGEventMessage': oms_event['oraEMNGEventMessage'][:255],
                      'oraEMNGEventMessageURL': oms_event['oraEMNGEventMessageURL'][:255],
                      'oraEMNGEventContextAttrs': oms_event['oraEMNGEventContextAttrs'][:255],
                      'oraEMNGEventTargetName': oms_event['oraEMNGEventTargetName'].replace(
                          '.severstal.severstalgroup.com', '')})

    # Во-вторых, для инцидентов и проблем не передается в переменную SequenceID
    # Будем брать его из SequenceID породившего события
    if oms_event['oraEMNGIssueType'] in ('2', '3'):
        logging.debug('Message is incident or problem')
        oms_event.update(
            {'oraEMNGEventIssueId': re.search('&issueID=([ABCDEF|0-9]{32})$',
                                              environment['MESSAGE_URL']).group(1)})

        emcli = Emcli()
        event_id = emcli.get_event_id(oms_event['oraEMNGEventIssueId'])
        if event_id is not None and len(event_id) != 0:
            logging.debug('Got event ID from OEM %s' % ', '.join(event_id))
            oms_event.update({'oraEMNGEventSequenceId': event_id[0]})
        else:
            logging.debug('Event ID not found in OEM')
            oms_event.update({'oraEMNGEventSequenceId': oms_event['oraEMNGEventIssueId']})

        # В-третьих, нужно проверить, есть ли событие с таким же уровнем severity
        # и отправлялось ли по нему сообщение
        # Если есть, трап по инциденту или проблеме отправлять не нужно
        message_sent = emcli.check_message_sent(oms_event['oraEMNGEventIssueId'],
                                                oms_event['oraEMNGEventSeverity'])

        # Подождем 2 секунды, возможно сообщение по событию запаздывает
        if not message_sent:
            logging.debug('Message from OEM not sent')
            time.sleep(2)
            message_sent = emcli.check_message_sent(oms_event['oraEMNGEventIssueId'],
                                                    oms_event['oraEMNGEventSeverity'])

        if message_sent:
            logging.debug('Message from OEM sent, skipping')
            do_not_send_trap = True
            reason = 'Message from OEM sent, skipping'
            # Если пришел Acknowledged, трап посылаем с ID породившего события
            if oms_event['oraEMNGAssocIncidentAcked'] == 'Yes':
                logging.debug('... But it is an Acknowledge message, sending')
                do_not_send_trap = False

        # Если пришла закрывашка, а само событие закрылось без отправки сообщения,
        # нужно отправить трап, подменив SequenceID на аналогичный параметр события
        if oms_event['oraEMNGEventSeverity'] == 'Clear':
            logging.debug('Clear message came')
            do_not_send_trap = False

    # Проверяем, если пришла закрывашка, а открывающего события в Заббиксе нет, отправлять не будем
    try:
        if oms_event['oraEMNGEventSeverity'] == 'Clear' or oms_event['oraEMNGAssocIncidentAcked'] == 'Yes':
            request = get_event_by_id(oms_event['oraEMNGEventSequenceId'])
            if request is None or len(request) == 0:
                do_not_send_trap = True
                reason = 'Clear\\acknowledge message came, Open message doesn\'t exists'

        else:
            logging.debug('Opening message exists in Zabbix')
            do_not_send_trap = do_not_send_trap
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e

    # Проверяем, если пришла закрывашка, будем закрывать через API, не будем отправлять
    try:
        if oms_event['oraEMNGEventSeverity'] == 'Clear' or oms_event['oraEMNGAssocIncidentAcked'] == 'Yes':
            logging.debug('Trying to acknowledge event to close it by API method')
            result = acknowledge_event_by_id(oms_event['oraEMNGEventSequenceId'])
            if result is not None and len(result) != 0:
                if 'TrapState' not in oms_event:
                    oms_event.update({'TrapState': 'closed by api'})
                do_not_send_trap = True
                reason = 'closed by API'
            else:
                do_not_send_trap = do_not_send_trap
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e

    # Проверяем, нет ли случайно в Заббиксе события с таким же текстом
    # отображаемого на экране
    # Если есть - отсылать его не нужно
    try:
        if check_if_message_exists(
                '%s %s %s: %s Acknowledge=%s' % (oms_event['oraEMNGEventSequenceId'],
                                                 oms_event['oraEMNGEventSeverity'],
                                                 oms_event['oraEMNGEventTargetName'],
                                                 oms_event['oraEMNGEventMessage'],
                                                 oms_event['oraEMNGAssocIncidentAcked'])) and not (
                oms_event['oraEMNGEventSeverity'] == 'Clear' or oms_event['oraEMNGAssocIncidentAcked'] == 'Yes'):
            logging.debug('Message exists in Zabbix, skipping')
            do_not_send_trap = True
            reason = 'Repeated message'
        else:
            logging.debug('Message do not exists in Zabbix')
            do_not_send_trap = do_not_send_trap
    except Exception as e:
        log_event(oms_event_to_log=oms_event)
        raise e

    # Если не стоит признак не посылать трап,
    if not do_not_send_trap:
        # Проверяем, нужно ли фильтровать трап
        # Если да - отсылать не будем
        if not filter_trap(message=oms_event['oraEMNGEventMessage'] if 'oraEMNGEventMessage' in oms_event else None,
                           event_name=oms_event['oraEMNGEventName'] if 'oraEMNGEventName' in oms_event else None):
            logging.debug('Message not filtered')
            # Для начала закроем событие в заббиксе с таким же ИД
            # если таковой имеется
            # но не трогаем закрывашки
            try:
                if not oms_event['oraEMNGEventSeverity'] == 'Clear' and not oms_event[
                                                                                'oraEMNGAssocIncidentAcked'] == 'Yes':
                    logging.debug('Trying to acknowledge event in Zabbix')
                    acknowledge_event_by_id(oms_event['oraEMNGEventSequenceId'])
            except Exception as e:
                log_event(oms_event_to_log=oms_event)
                raise e

            # Отправляем SNMPv1 трап
            send_snmp_trap(oms_event)

            # Отправляем Zabbix трап
            # В дальнейшем от одного из этих методов можно будет отказаться
            # Пока делаем так
            send_zabbix_trap(oms_event)
        else:
            logging.debug('Event filtered')
            if 'TrapState' not in oms_event:
                oms_event.update({'TrapState': 'filtered'})
    else:
        logging.debug('Event skipped')
        if 'TrapState' not in oms_event:
            oms_event.update({'TrapState': 'skipped, reason: %s' % reason})

    log_event(oms_event_to_log=oms_event)

    # Возвращаем полученный SequenceID
    return '%s: %s' % (oms_event['oraEMNGEventSequenceId'], oms_event['TrapState'])
