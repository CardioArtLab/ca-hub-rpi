import logging

LOG = logging.getLogger('usb2mq')
formatter = logging.Formatter('%(levelname)s [%(name)s]: %(asctime)s %(message)s', datefmt='%m/%d/%Y %I:%M:%S %p')
h = logging.StreamHandler()
h.setFormatter(formatter)
LOG.setLevel(logging.INFO)
LOG.addHandler(h)
