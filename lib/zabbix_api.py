# coding=utf-8

import os
import json
import logging
from pyzabbix import ZabbixAPI


def get_config():
    # получаем конфиг для логина на сервере Заббикса
    # конфиг представляет собой файл формата JSON с 5 записями:
    # 1. server - URL сервера Заббикса
    # 2. name - имя пользователя для логина
    # 3. password - пароль пользователя из п.2
    # 4. message - сообщение, с которым подтверждается или закрывается событие
    # 5. action - признак, закрывать или нет
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        return json.load(json_file)


def get_zabbix():
    # коннектимся к Заббиксу
    # возвращаем объект ZabbixAPI
    logging.debug('Connecting to Zabbix')
    config = get_config()

    return ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])


def get_event_by_id(event_id):
    # ищем проблему в Заббиксе
    # для поиска используем SequenceId, которое должно быть уникальным в пределах всего ОЕМ
    # возвращаем zabbix_api.problem. На выходе получаем JSON, который можно разбирать как душе угодно
    logging.debug('Trying to get event in Zabbix by ID')

    # получаем коннект к Заббиксу
    zabbix_api = get_zabbix()
    # формируем запрос
    request = zabbix_api.problem.get(output='eventid', tags=[{'tag': 'ID', 'value': event_id}])
    logging.debug('Found some events in Zabbix')

    return request


def acknowledge_event_by_id(event_id):
    # подтверждаем проблему в Заббиксе
    # если в настройках указано, то и закрываем. за это отвечает поле action, для закрытия установлено в значение 1
    logging.debug('Trying to get event in Zabbix by ID')

    # на всякий случай, вдруг событий с таким ID несколько, возвращаем list
    result = list()
    # находим события с таким ID
    request = get_event_by_id(event_id)

    # получаем коннект к Заббиксу
    zabbix_api = get_zabbix()
    # получаем конфиг
    config = get_config()
    # циклом бежим по событиям и подтвеждаем их
    for event in request:
        ack_request = zabbix_api.event.acknowledge(eventids=event['eventid'], message=config['message'],
                                                   action=config['action'])
        logging.debug('Acknowledged event')
        result.append(ack_request)

    return result


def check_if_message_exists(message):
    # проверям, существует ли требуемое сообщение в Заббиксе
    # ищем по тексту сообщения
    logging.debug('Trying to check if message exists in Zabbix')

    # получаем коннект к Заббиксу
    zabbix_api = get_zabbix()
    # проверяем, есть ли события, относящиеся к нашей группе
    # если нет, то и проверять нечего
    events = zabbix_api.problem.get(groupids='157')
    if len(events) != 0:
        # события есть. Получем все элементы данных, относящихся к нашей группе
        items = zabbix_api.item.get(extendoutput=True, selectTriggers='extend', selectHosts='extend', groupids='157')

        for item in items:
            # в цикле бежим по ним
            # если к элементу данных не привязан триггер - пропускаем его, он не мог породить проблему
            if len(item['triggers']) != 0:
                for event in events:
                    # в цикле бежим по всем событиям нашей группы
                    # ищем триггер, котрый породил наше событие
                    object_id = event['objectid']
                    clock = event['clock']
                    for trigger in item['triggers']:
                        # если нашли такой триггер
                        if trigger['triggerid'] == object_id:
                            # вытаскиваем всю историю по этому триггеру,
                            # у которой отметка времени совпадает с отметкой нашего события
                            item_id = item['itemid']
                            history_items = zabbix_api.history.get(extendOutput=True, history=4, itemids=item_id,
                                                                   filter={'clock': clock})
                            for history_item in history_items:
                                # в цикле бежим по истории
                                # если у исторического элемента сообщение совпадает с требуемым - возвращаем True
                                if message.encode('utf-8') in history_item['value'].encode('utf-8'):
                                    logging.debug('Trigger found in Zabbix')
                                    return True

    else:
        logging.debug('Trigger not found in Zabbix')
        return False

    logging.debug('Trigger not found in Zabbix')
    return False
