#!/bin/python

import daemon
import signal
import sys
import lockfile

def main():
	print 'test'

def shutdown(signum, frame):
	sys.exit(0)

with daemon.DaemonContext(
	stdout=sys.stdout,
	stderr=sys.stderr,
	signal_map = {
		signal.SIGTERM: shutdown,
		signal.SIGTSTP: shutdown
	}, 
	pidfile = lockfile.FileLock('/var/run/ca-hub-rpi.pid')):
	main()
