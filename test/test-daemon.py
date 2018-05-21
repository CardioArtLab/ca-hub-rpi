#!/bin/python

import daemon
import signal
import sys
import lockfile
import logging
import ConfigParser
from time import sleep

""" Load config file """
config = ConfigParser.SafeConfigParser({
            'pidfile': './ca-hub-rpi.pid',
            'logfile': './ca-hub-rpi.log',
            'workdir': './'
        })
config.read('./config.ini')

""" Log configuration """
log = logging.getLogger('process')
formatter = logging.Formatter('%(levelname)s [%(name)s]: %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
#fileHandler = logging.FileHandler(config.get('process', 'logfile'), mode='a')
#fileHandler.setFormatter(formatter)
streamHandler = logging.StreamHandler()
streamHandler.setFormatter(formatter)
log.setLevel(logging.INFO)
#log.addHandler(fileHandler)
log.addHandler(streamHandler)

def main():    
    log = logging.getLogger('process')
    log.info('initialize')
    while True:
        log.info('processing...')
        sleep(1)

def shutdown(signum, frame):
    log = logging.getLogger('process')
    log.info('shutdown...')
    sys.exit(0)

with daemon.DaemonContext(
    stdout = sys.stdout,
    stderr = sys.stderr,
    signal_map = {
        signal.SIGINT: shutdown,
        signal.SIGTERM: shutdown,
        signal.SIGTSTP: shutdown
    }, 
    umask = 0o022,
    files_preserve = None,
    working_directory = config.get('process', 'workdir'),
    pidfile = lockfile.FileLock(config.get('process', 'pidfile'))):

    main()