# coding=utf-8

import os
import json
from pyzabbix import ZabbixAPI


def acknowledge_event_by_id(event_id):
    result = list()
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)

    zabbix_api = ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])
    request = zabbix_api.event.get(output='eventid', value=1, acknowledged=False,
                                   tags=[{'tag': 'ID', 'value': event_id}])

    for event in request:
        ack_request = zabbix_api.event.acknowledge(eventids=event['eventid'], message=config['message'],
                                                   action=config['action'])
        result.append(ack_request)

    return result


def check_if_message_exists(message):
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)

    zabbix_api = ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])
    request = zabbix_api.trigger.get(extendoutput=True, expandData=1, expandDescription=1, withUnacknowledgedEvents=1,
                                     only_true=1)

    return True if message.encode('ascii') in [trigger['description'].encode('utf-8') for trigger in request] else False
