import logging
from daemonize import Daemonize

import ConfigParser
from time import sleep

""" Load config file """
config = ConfigParser.SafeConfigParser({
            'pidfile': './ca-hub-rpi.pid',
            'logfile': './ca-hub-rpi.log',
            'workdir': './'
        })
config.read('./config.ini')
pidfile = config.get('process', 'pidfile')
logger = logging.getLogger('process')
formatter = logging.Formatter('%(levelname)s [%(name)s]: %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
fh = logging.FileHandler(config.get('process', 'logfile'), 'w')
fh.setFormatter(formatter)
logger.setLevel(logging.DEBUG)
logger.addHandler(fh)

def main():    
    logger.info('initialize')
    while True:
        logger.info('processing...')
        sleep(1)

daemon = Daemonize(app='ca-hub-rpi', pid=pidfile, action=main, keep_fds=[])
daemon.start()