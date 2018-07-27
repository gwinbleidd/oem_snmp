#!/bin/python
# coding=utf-8

from emcli import *

start = datetime.datetime.now()

emcli = Emcli()

print emcli.get_event_id('71E4097171ECBA19E0534539780ACF99')

# print emcli.configured

print datetime.datetime.now() - start
