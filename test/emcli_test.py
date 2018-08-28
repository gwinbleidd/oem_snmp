#!/bin/python
# coding=utf-8

import sys
import os
import logging

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'lib'))

from emcli import *


def main():
    log_filename = os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, 'log', 'test.log')
    logging.basicConfig(filename=log_filename, level=logging.INFO,
                        format="%(asctime)s - %(process)d - %(levelname)s - %(message)s")

    start = datetime.datetime.now()
    try:
        emcli = Emcli()
        print emcli.get_event_id('71E4097171ECBA19E0534539780ACF99')
        logging.info('Time spent: %s' % str(datetime.datetime.now() - start))
    except Exception as e:
        logging.error(e, exc_info=True)


if __name__ == "__main__":
    main()
