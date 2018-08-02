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
        request = zabbix_api.event.get(objectids=243285, selectTags='extend')
        print json.dumps(request, indent=3)
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()
