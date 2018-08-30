#!/usr/bin/python2.7
# coding=utf-8

import os
import sys
import json
from pyzabbix import ZabbixAPI
import logging
import socket


def main():
    log_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'test.log')
    logging.basicConfig(filename=log_filename, level=logging.DEBUG,
                        format="%(asctime)s - %(process)d - %(levelname)s - %(message)s")
    config_file = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, '.secure', '.zabbix.json')
    with open(config_file, 'r') as json_file:
        config = json.load(json_file)

    try:
        zabbix_api = ZabbixAPI(url=config['server'], user=config['name'], password=config['password'])

        request = zabbix_api.hostgroup.get(filter={'name': 'Сервис. Oracle'})
        groupid_oem = request[0]['groupid']
        request = zabbix_api.hostgroup.get(filter={'name': 'Сервис. Oracle. New OEM'})
        groupid_oem_new = request[0]['groupid']

        hosts = list()
        request = zabbix_api.host.get(groupids=groupid_oem,
                                      output=['host', 'name'],
                                      selectGroups='extend',
                                      selectInterfaces='extend')
        if len(request) != 0:
            for host in request:
                not_new = True
                for group in host['groups']:
                    if group['groupid'] == groupid_oem_new:
                        not_new = False

                if not_new:
                    hosts.append(host)

                    if '.severstalgroup.com' not in host['host']:
                        zabbix_api.host.update(hostid=host['hostid'], name=host['host'],
                                               host=host['host'] + '.example.com')

                    if '.severstalgroup.com' in host['name']:
                        zabbix_api.host.update(hostid=host['hostid'],
                                               name=host['name'].split('.')[0])

                    for interface in host['interfaces']:
                        if interface['dns'] == 'oem-vm.example.com':
                            zabbix_api.hostinterface.update(interfaceid=interface['interfaceid'], ip='127.0.0.1',
                                                            dns='oem01.example.com')

            print json.dumps(hosts, indent=3, ensure_ascii=False).encode('utf8')
    except Exception as e:
        logging.error(e, exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
