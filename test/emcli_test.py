#!/bin/python
# coding=utf-8

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from emcli import *


def main():
    log_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'emcli.log')
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format="%(asctime)s - %(process)d - %(levelname)s - %(message)s")

    start = datetime.datetime.now()
    try:
        emcli = Emcli()
        resource = 'Targets'
        columns = 'TARGET_NAME,TARGET_TYPE,HOST_NAME'
        hostname = 'HOST_NAME=\'lu142-vm.example.com\''
        result = emcli.execute('list', '-resource=%s' % resource, '-search=%s' % hostname, '-columns=%s' % columns,
                               '-format=name:csv')
        targets = [x.replace('\n', '').split(',') for x in result][1:]
        for target in targets:
            property_department = '{target_name}@{target_type}@Department@Example'.format(
                target_name=target[0], target_type=target[1])
            property_location = '{target_name}@{target_type}@Location@Example'.format(
                target_name=target[0], target_type=target[1])
            property_lob = '{target_name}@{target_type}@Line of Business@Example'.format(
                target_name=target[0], target_type=target[1])
            property_severity = '{target_name}@{target_type}@Severity@Example'.format(
                target_name=target[0], target_type=target[1])
            property_lifecycle_status = '{target_name}@{target_type}@Lifecycle Status@Standby/Test'.format(
                target_name=target[0], target_type=target[1])
            property_records = '{property_department};{property_location};{property_lob};{property_severity};{property_lifecycle_status}'.format(
                property_department=property_department,
                property_location=property_location,
                property_lob=property_lob,
                property_severity=property_severity,
                property_lifecycle_status=property_lifecycle_status)
            # print property_records
            subseparator = '@'
            target_set = emcli.execute('set_target_property_value', '-property_records=%s' % property_records, '-subseparator=property_records=%s' % subseparator)
            print target_set
        logging.info('Time spent: %s' % str(datetime.datetime.now() - start))
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()
