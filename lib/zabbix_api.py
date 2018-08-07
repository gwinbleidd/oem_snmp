# coding=utf-8

import os
import json
import logging
from pyzabbix import ZabbixAPI


def acknowledge_event_by_id(event_id):
    logging.debug('Trying to acknowledge event in Zabbix by ID')
    result = list()
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)

    logging.debug('Connecting to Zabbix')
    zabbix_api = ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])
    request = zabbix_api.event.get(output='eventid', value=1, acknowledged=False,
                                   tags=[{'tag': 'ID', 'value': event_id}])
    logging.debug('Found some events in Zabbix')

    for event in request:
        ack_request = zabbix_api.event.acknowledge(eventids=event['eventid'], message=config['message'],
                                                   action=config['action'])
        logging.debug('Acknowledged event')
        result.append(ack_request)

    return result


def check_if_message_exists(message):
    logging.debug('Trying to check if message exists in Zabbix')
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)

    logging.debug('Connecting to Zabbix')
    zabbix_api = ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])
    request = zabbix_api.trigger.get(extendoutput=True, expandData=1, expandDescription=1, withUnacknowledgedEvents=1,
                                     only_true=1)

    if message.encode('ascii') in [trigger['description'].encode('utf-8') for trigger in request]:
        logging.debug('Trigger found in Zabbix')
        return True
    else:
        logging.debug('Trigger not found in Zabbix')
        return False
