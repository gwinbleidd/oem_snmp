#!/bin/python
# coding=utf-8

import logging
import os
import sys

from trap_sender import *

LOG_FILENAME = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'application.log')
logging.basicConfig(filename=LOG_FILENAME, level=logging.DEBUG,
                    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")

environment = {"ASSOC_EVENT_COUNT": "1",
               "CATEGORIES_COUNT": "1",
               "CATEGORY_1": "Fault",
               "CATEGORY_CODES_COUNT": "1",
               "CATEGORY_CODE_1": "Fault",
               "ESCALATED": "No",
               "ESCALATED_LEVEL": "0",
               "EVENT_SOURCE_1_HOST_NAME": "test-db02-vm.severstal.severstalgroup.com",
               "EVENT_SOURCE_1_TARGET_GUID": "70B891A7A62D0E8BE0534539780A144B",
               "EVENT_SOURCE_1_TARGET_NAME": "TSTDB02.severstal.severstalgroup.com",
               "EVENT_SOURCE_1_TARGET_OWNER": "VS.POTAPOV",
               "EVENT_SOURCE_1_TARGET_TYPE": "oracle_database",
               "EVENT_SOURCE_1_TARGET_URL": "https://oem-vm.severstal.severstalgroup.com:7803/em/redirect?pageType=TARGET_HOMEPAGE&targetName=TSTDB02.severstal.severstalgroup.com&targetType=oracle_database",
               "EVENT_SOURCE_1_TARGET_VERSION": "12.1.0.2.180717",
               "EVENT_SOURCE_COUNT": "1",
               "INCIDENT_ACKNOWLEDGED_BY_OWNER": "No",
               "INCIDENT_CREATION_TIME": "Jul 24, 2018 5:17:53 PM MSK",
               "INCIDENT_ID": "3242",
               "INCIDENT_OWNER": "",
               "INCIDENT_STATUS": "New",
               "ISSUE_TYPE": "2",
               "LAST_UPDATED_TIME": "Jul 24, 2018 5:17:53 PM MSK",
               "MESSAGE": "1 distinct types of ORA- errors have been found in the alert log.",
               "MESSAGE_URL": "https://oem-vm.severstal.severstalgroup.com:7803/em/redirect?pageType=sdk-core-event-console-detailIncident&issueID=71C06D8FA72475F8E0534539780A9933",
               "NOTIF_TYPE": "NOTIF_NORMAL",
               "ORCL_GTP_OS": "Linux",
               "ORCL_GTP_PLATFORM": "x86_64",
               "PRIORITY": "None",
               "PRIORITY_CODE": "PRIORITY_NONE",
               "REPEAT_COUNT": "0",
               "RULESET_NAME": "All",
               "RULE_NAME": "All,Call OS script on incident",
               "RULE_OWNER": "SYSMAN",
               "SEVERITY": "Warning",
               "SEVERITY_CODE": "WARNING",
               "SEVERITY_SHORT": "W",
               "UPDATES": "<br>Incident created by rule (Name = All, Call OS script on event and create incident; Owner = SYSMAN).",
               "UPDATES_1": "Incident created by rule (Name = All, Call OS script on event and create incident; Owner = SYSMAN).",
               "UPDATES_COUNT": "1",
               "USER_DEFINED_TARGET_PROP": "Platform=x86_64, Operating System=Linux"}

try:
    sequence_id = send_trap(environment)
    logging.debug(sequence_id)
    print sequence_id
except Exception as e:
    logging.error(e, exc_info=True)
    sys.exit(1)
