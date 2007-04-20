#!/usr/bin/env python
#
# pymailheaders.py
# Copyright 2007 Neil Shi <zeegeek@gmail.com>
#
# Main program of pymailheaders
# This file creates mail fetching thread and gui thread.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

from threading import Thread
from threading import Lock
from threading import Event
from optparse import OptionParser
import sys
import re
import os
import os.path

import gui
import imapprl
import popprl
import feedprl
import config
import constants
from exception import *

basedir = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(os.path.join(basedir, '%s.py' % constants.NAME)):
	if os.path.exists(os.path.join(os.getcwd(), '%s.py' % constants.NAME)):
		basedir = os.getcwd()
sys.path.insert(0, basedir)
os.chdir(basedir)

# global varibals
lock = Lock()
messages = []

class mail_thread(Thread):
	"""This class creates the thread for fetching messages.

	@note: Private member variables:
		__interval
		__mail_obj
	"""

	def __init__(self, t, server, uname, password, ssl, interval, \
		     mbox = 'INBOX'):
		"""Override constructor

		@type t: string
		@param t: server type
		@type server: string
		@param server: mail server address
		@type uname: string
		@param uname: username
		@type password: string
		@param password: password
		@type ssl: bool
		@param ssl: if this is a secure connection
		@type interval: int
		@param interval: time interval between updates
		@type mbox: string
		@param mbox: mailbox.
			I{Default = 'INBOX'}
		"""

		Thread.__init__(self)
		self.__interval = float(interval)
		if not globals().has_key('%sprl' % t):
			print >> sys.stderr, \
			      'pymailheaders: unknown server type'
			sys.exit(1)
		self.__mail_obj = getattr(globals()['%sprl' % t], t)(server, \
								     uname, \
								     password, \
								     ssl, \
								     mbox)
		self.timer = Event()

	def __del__(self):
		"""Override destructor

		Should delete the objects created on construction properly.
		"""

		del self.__mail_obj

	def fetch(self):
		"""Check and get mails

		This will set the global variables messages.
		"""
		
		global messages
		global lock

		try:
			lock.acquire()
			messages = self.__mail_obj.get_mail()
			lock.release()
		except Exception, strerr:
			messages = [(True, 'Error', str(strerr))]
			lock.release()
			self.connect()
			
	def connect(self):
		"""Connect to the server.
		"""

		global messages
		global lock

		try:
			self.__mail_obj.connect()
		except TryAgain:
			lock.acquire()
			messages = [(True, 'Error', 'Network not available')]
			lock.release()
		except Exception, strerr:
			lock.acquire()
			messages = [(True, 'Error', str(strerr))]
			lock.release()

	def run(self):
		"""Connect to the server and fetch for the first time
		"""

		global gui_thr
		self.connect()
		while not self.timer.isSet():
			self.fetch()
			gui.gobject.idle_add(update_gui)
			self.timer.wait(self.__interval)

# update GUI
def update_gui():
	global lock
	global messages
	global gui_thr

	lock.acquire()
	gui_thr.display(messages)
	lock.release()

def main():
	"""Main function
	"""

	global lock
	global gui_thr
	global messages

	# parse command-line arguments
	usage = 'usage: %prog [options]... args...'
	parser = OptionParser(usage)
	parser.add_option('-t', '--type', dest = 'type', \
			  help = 'server type: imap, pop, feed')
	parser.add_option('-s', '--server', dest = 'server', \
			  help = 'server to connect to')
	parser.add_option('-a', '--auth', action='store_true', \
			  dest = 'auth', \
			  help = 'server requires authentication')
	parser.add_option('-u', '--username', dest = 'username', \
			  help = 'username to log onto the server')
	parser.add_option('-p', '--password', dest = 'password', \
			  help = 'password')
	parser.add_option('-e', '--ssl', action = 'store_true', \
			  dest = 'encrypted', help = 'user SSL for the server')
	parser.add_option('-i', '--interval', dest = 'interval', \
			  type = 'int', help = 'update interval in seconds')
	parser.add_option('-f', '--config-file', dest = 'config', \
			  help = 'configuration file path')
	parser.add_option('-w', '--width', dest = 'width', type = 'int', \
			  help = 'width of the window')
	parser.add_option('-g', '--height', dest = 'height', type = 'int', \
			  help = 'height of the window')
	parser.add_option('--bg', dest = 'background', help = 'backgound color')
	parser.add_option('--fg', dest = 'foreground', \
			  help = 'foreground color')
	parser.add_option('--fgn', dest = 'foreground new', \
			  help = 'foreground color for new messages')
	(options, args) = parser.parse_args()

	if options.config:
		config_file = os.path.expanduser(options.config)
	else:
		# default config file location
		config_file = os.path.expanduser('~/.pymailheadersrc')

	try:
		# read in config file if there is any
		conf = config.config(config_file)
	except:
		sys.exit(1)

	# get all configurations
	# 
	# command line arguments have higher priorities, so they can overwrite
	# config file options
	opts = conf.get_all()

	# this is way too ugly, it's not a proper use of optparse, but had to
	# use this hack to get arround.
	options = options.__dict__.copy()
	del options['config']

	# don't use opts.update() because that will write all None values
	for k in options.iterkeys():
		if not opts.has_key(k) or options[k] != None:
			opts[k] = options[k]
	del options

	# check args
	if opts['type'] == None or opts['server'] == None:
		parser.error('server type and server are required.')
	if opts['auth'] and (opts['username'] == None or \
			     opts['password'] == None):
		parser.error('username and password are needed ' + \
			     'for authentication.')
	
	# create threads
	gui_thr = gui.gui(opts)
	mail_thr = mail_thread(opts['type'], opts['server'], \
			       opts['username'], opts['password'], \
			       opts['encrypted'], opts['interval'])
	del opts

	try:
		# start thread
		mail_thr.start()
		gui.gtk.main()
	except KeyboardInterrupt:
		pass

	# stop mail thread
	mail_thr.timer.set()

	# save settings
	opts = gui_thr.get_settings()
	for k, v in opts.iteritems():
		conf.set(k, v)

	# clean up the mess
	del mail_thr
	del gui_thr
	
# rock n' roll
if __name__ == '__main__':
	main()
