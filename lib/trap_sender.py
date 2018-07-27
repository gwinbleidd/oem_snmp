# coding=utf-8

from pysnmp.hlapi import *
import socket
import re
import time
import os
import json

from event_logger import log_event
from emcli import Emcli


def send_trap(environment):
    # Выставляем признак неотправки трапа
    do_not_send_trap = False

    # Загружаем конфиг
    with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'config',
                           'snmp.json'), 'r') as json_file:
        config = json.load(json_file)

    # Маппинг переменных окружения в переменные трапа в соответствии с MIBом
    # # Переменные перечислены в соответсвии с главой
    # # "3.10.2 Passing Event, Incident, Problem Information to an OS Command or Script"
    # # документа Oracle® Enterprise Manager Cloud Control Administrator's Guide
    # # Если зачению переменной трапа может соответствовать несколько переменных окружения
    # # в зависимости от события, которое обрабатывается, такие переменные представлены
    # # в виде словаря, в которых ключ соответствует переменной ISSUE_TYPE - тип события,
    # # значение - переменной, которую нужно подставить
    trap_to_environment_variables = config['trap_to_environment_variables']

    # Все поля трапа OEM, которые мы будем передавать, получены из MIBа omstrap.v1
    trap_parameters = config['trap_parameters']

    # Имя хоста ОЕМ
    hostname = config['hostname']

    # На вход получаем параметры окружения в виде словаря, которые создает OMS при вызове скрипта
    # Собираем только те параметры, которые укладываются в стандартный MIB omstrap.v1 Oracle OEM 13c
    # Кроме того, сохраняем в oms_event['oraEMNGEnvironment'] все переменные окружения, мало ли что-то упустили

    oms_event = {'oraEMNGEnvironment': environment,
                 'oraEMNGEventSequenceId': 'null'}

    if 'ISSUE_TYPE' not in environment:
        raise Exception('ISSUE_TYPE not set')

    for trap_variable, os_variable in trap_to_environment_variables.iteritems():
        if type(os_variable) is unicode:
            oms_event.update({trap_variable: environment[os_variable] if os_variable in environment else ''})
        elif type(os_variable) is dict:
            issue_type = environment['ISSUE_TYPE']
            oms_event.update({trap_variable: environment[os_variable[issue_type]] if (issue_type in os_variable and
                                                                                      os_variable[
                                                                                          issue_type] in environment) else ''})

    # Нужно подправить некоторые элементы
    # Во-первых, подрезаем длину сообщения и URL события до 255 символов, чтобы влезало в трап
    oms_event.update({'oraEMNGEventMessage': oms_event['oraEMNGEventMessage'][:255],
                      'oraEMNGEventMessageURL': oms_event['oraEMNGEventMessageURL'][:255],
                      'oraEMNGEventContextAttrs': oms_event['oraEMNGEventContextAttrs'][:255]})

    # Во-вторых, для инцидентов и проблем не передается в переменную SequenceID, но его можно взять из поля MESSAGE_URL
    if oms_event['oraEMNGIssueType'] in ('2', '3'):
        oms_event.update(
            {'oraEMNGEventSequenceId': re.search('&issueID=([ABCDEF|0-9]{32})$',
                                                 environment['MESSAGE_URL']).group(1)})

        # В-третьих, нужно проверить, есть ли событие с таким же уровнем severity
        # Если есть, трап по инциденту или проблеме отправлять не нужно
        emcli = Emcli()
        result = emcli.get_event_id(oms_event['oraEMNGEventSequenceId'], oms_event['oraEMNGEventSeverity'])
        if len(result) == 1:
            do_not_send_trap = True

            # Если пришла закрывашка, а само событие закрылось без отправки сообщения,
            # нужно отправить трап, подменив SequenceID на аналогичный параметр события
            if oms_event['oraEMNGEventSeverity'] == 'Clear':
                if not emcli.check_message_sent(oms_event['oraEMNGEventSequenceId'], oms_event['oraEMNGEventSeverity']):
                    result = emcli.get_event_id(oms_event['oraEMNGEventSequenceId'])
                    if len(result) == 1:
                        oms_event['oraEMNGEventSequenceId'] = result[0]
                        do_not_send_trap = False

    # Складывает полученные параметры окружения в виде json'а в файл, чтобы была возможность анализа при необходимости
    # Пишем в каталог логов ../log
    # Для того, чтобы получить валидный json, перед сохранением проверяем, пустой ли файл.
    # Если непустой, читаем, добавляем еще один узел в json и перезаписывам

    log_event(oms_event_to_log=oms_event)

    # Если не стоит признак не посылать трап,
    if not do_not_send_trap:
        # Собираем трап
        # Для этого нужен MIB (Management Information Base)
        # # Есть проблема, Питон не хочет подхватывать напрямую MIB-файл из OMS,
        # # который лежит $OMS_HOME/network/doc/omstrap.v1. Кроме того, в дефолтном файле
        # # слишком много ненужной (устаревшей) информации. Поэтому мы удалили все OIDы oraEM4Alert,
        # # кроме тех которые необходимы для копиляции. После этого скомпилировали полученный MIB
        # # скриптом mibdump.py, который идет в поставке с пакетом pysmi, который ставиться pip'ом
        # # и положил полученный *.py файл в /usr/lib/python2.7/site-packages/pysnmp/smi/mibs с правами 644

        address = socket.gethostbyname(hostname)

        # Собираем переменные трапа
        trap_variables = [(ObjectIdentity('DISMAN-EVENT-MIB', 'sysUpTimeInstance'), TimeTicks(int(time.time()))),
                          (ObjectIdentity('SNMP-COMMUNITY-MIB', 'snmpTrapAddress', 0), address)]

        for trap_variable in trap_parameters:
            trap_variables.append((ObjectIdentity('ORACLE-ENTERPRISE-MANAGER-4-MIB', trap_variable),
                                   oms_event[trap_variable] if trap_variable in oms_event else ''))

        # Посылаем трап
        try:
            errorindication, errorstatus, errorindex, varbinds = next(
                sendNotification(
                    SnmpEngine(),
                    CommunityData('public', mpModel=0),
                    UdpTransportTarget(('10.120.47.136', 162)),
                    ContextData(),
                    'trap',
                    NotificationType(
                        ObjectIdentity('ORACLE-ENTERPRISE-MANAGER-4-MIB', 'oraEMNGEvent')
                    ).addVarBinds(*trap_variables)
                )
            )

            if errorindication:
                raise Exception(errorindication)
        except Exception as e:
            raise e

    # Возвращаем полученный SequenceID
    return oms_event['oraEMNGEventSequenceId']
