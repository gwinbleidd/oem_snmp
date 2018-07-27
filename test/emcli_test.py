#!/bin/python
# coding=utf-8

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from emcli import *

start = datetime.datetime.now()

emcli = Emcli()

print emcli.get_event_id('71E4097171ECBA19E0534539780ACF99')

# print emcli.configured

print datetime.datetime.now() - start
