#!/bin/python
# coding=utf-8

import os
import json
from pyzabbix import ZabbixAPI
import logging


def main():
    log_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'test.log')
    logging.basicConfig(filename=log_filename, level=logging.DEBUG,
                        format="%(asctime)s - %(process)d - %(levelname)s - %(message)s")
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)

    try:
        zabbix_api = ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])

        request = zabbix_api.event.get(output='eventid', value=1, acknowledged=False,
                                       tags=[{'tag': 'ID', 'value': '72C65E6861CD4F7FE0534539780ACC89'}])

        # events = zabbix_api.event.get(value=1, acknowledged=False, groupids='157')
        # if len(events) != 0:
        #     items = zabbix_api.item.get(extendoutput=True, selectTriggers='extend', selectHosts='extend',
        #                                 groupids='157')
        #     for item in items:
        #         if len(item['triggers']) != 0:
        #             for event in events:
        #                 object_id = event['objectid']
        #                 clock = event['clock']
        #                 for trigger in item['triggers']:
        #                     if trigger['triggerid'] == object_id:
        #                         item_id = item['itemid']
        #                         history_items = zabbix_api.history.get(extendOutput=True, history=4, itemids=item_id,
        #                                                                filter={'clock': clock})
        #                         for history_item in history_items:
        #                             # if history_item['clock'].encode('ascii') == clock:
        #                             print json.dumps(history_item, indent=3)
        # request = zabbix_api.trigger.get(extendOutput=True, expandDescription=1, triggerids=228628, lastChangeSince=1533809664)
        # request = zabbix_api.history.get(extendOutput=True, history=4, itemids='418930')
        # request = zabbix_api.trigger.get(extendOutput=True, expandData=1, expandDescription=1, expandExpression=1, skipDependent=1,
        #                                  groupids='157', selectItems='extend', filter={'value': '1'},
        #                                  output=['triggerid',
        #                                          'description',
        #                                          'priority'])
        print json.dumps(request, indent=3)
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()
