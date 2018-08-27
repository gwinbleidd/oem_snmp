# coding=utf-8

import os
import json
import logging
from pyzabbix import ZabbixAPI


def get_config():
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        return json.load(json_file)


def get_zabbix():
    logging.debug('Connecting to Zabbix')
    config = get_config()

    return ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])


def get_event_by_id(event_id):
    logging.debug('Trying to get event in Zabbix by ID')

    zabbix_api = get_zabbix()
    request = zabbix_api.problem.get(output='eventid', tags=[{'tag': 'ID', 'value': event_id}])
    logging.debug('Found some events in Zabbix')

    return request


def acknowledge_event_by_id(event_id):
    logging.debug('Trying to get event in Zabbix by ID')

    result = list()
    request = get_event_by_id(event_id)

    zabbix_api = get_zabbix()
    config = get_config()
    for event in request:
        ack_request = zabbix_api.event.acknowledge(eventids=event['eventid'], message=config['message'],
                                                   action=config['action'])
        logging.debug('Acknowledged event')
        result.append(ack_request)

    return result


def check_if_message_exists(message):
    logging.debug('Trying to check if message exists in Zabbix')

    zabbix_api = get_zabbix()
    events = zabbix_api.problem.get(groupids='157')
    if len(events) != 0:
        items = zabbix_api.item.get(extendoutput=True, selectTriggers='extend', selectHosts='extend', groupids='157')
        for item in items:
            if len(item['triggers']) != 0:
                for event in events:
                    object_id = event['objectid']
                    clock = event['clock']
                    for trigger in item['triggers']:
                        if trigger['triggerid'] == object_id:
                            item_id = item['itemid']
                            history_items = zabbix_api.history.get(extendOutput=True, history=4, itemids=item_id,
                                                                   filter={'clock': clock})
                            for history_item in history_items:
                                if message.encode('utf-8')[33:] == history_item['value'].encode('utf-8')[33:]:
                                    logging.debug('Trigger found in Zabbix')
                                    return True

    else:
        logging.debug('Trigger not found in Zabbix')
        return False

    logging.debug('Trigger not found in Zabbix')
    return False
