#!/bin/python
# coding=utf-8

import json
from pyzabbix import ZabbixMetric, ZabbixSender
import logging
import os

LOG_FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'test.log')
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

environment_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), 'environment.json')

with open(environment_file, 'r') as json_file:
    environment = json.load(json_file)

try:
    result = ZabbixSender('10.120.47.136').send([ZabbixMetric(environment['HOST_NAME'], 'data', json.dumps(environment, indent=3, sort_keys=True))])

    print(result)
except Exception as e:
    logging.error(e, exc_info=True)