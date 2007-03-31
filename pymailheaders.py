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

import gui
import imapprl
import popprl
import feedprl
from exception import *

# global varibals
lock = Lock()

class mail_thread(Thread):
	"""This class creates the thread for fetching messages.

	@note: Private member variables:
		__interval
		__mail_obj
	"""

	def __init__(self, t, server, uname, password, ssl, h, \
		     interval, mbox = 'INBOX'):
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
		@type h: int
		@param h: number of messages to fetch each time
		@type interval: int
		@param interval: time interval between updates
		@type mbox: string
		@param mbox: mailbox.
			I{Default = 'INBOX'}
		"""

		Thread.__init__(self)
		self.__interval = float(interval)
		if t == 'feed':
			self.__mail_obj = feedprl.feed(server, uname, \
						       password, ssl, h, mbox)
		elif t == 'imap':
			self.__mail_obj = imapprl.imap(server, uname, \
						       password, ssl, h, mbox)
		elif t == 'pop':
			self.__mail_obj = popprl.pop(server, uname, \
						     password, ssl, h, mbox)
		else:
			print >> sys.stderr, \
			      'pymailheaders: unknown server type'
			sys.exit(1)
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
			messages = [('Error', str(strerr))]
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
			messages = [('Error', 'Network not available')]
			lock.release()
		except Exception, strerr:
			lock.acquire()
			messages = [('Error', str(strerr))]
			lock.release()

	def run(self):
		"""Connect to the server and fetch for the first time
		"""

		global gui_thr

		self.connect()
		while not self.timer.isSet():
			self.fetch()
			gui_thr.event_generate('<<Update>>', when = 'tail')
			self.timer.wait(self.__interval)

def main():
	"""Main function
	"""

	# parse command-line arguments
	usage = 'usage: %prog [options]... args...'
	parser = OptionParser(usage)
	parser.add_option('-t', '--type', dest = 'server_type', \
			  help = 'server type: imap, pop, feed')
	parser.add_option('-s', '--server', dest = 'server', \
			  help = 'server to connect to')
	parser.add_option('-a', '--auth', action='store_true', \
			  dest = 'auth', default = False, \
			  help = 'server requires authentication')
	parser.add_option('-u', '--username', dest = 'username', default = '', \
			  help = 'username to log onto the server')
	parser.add_option('-p', '--password', dest = 'password', default = '', \
			  help = 'password')
	parser.add_option('-e', '--ssl', action = 'store_true', dest = 'ssl', \
			  default = False, help = 'user SSL for the server')
	parser.add_option('-i', '--interval', dest = 'interval', \
			  default = 180, help = 'update interval in seconds')
#	parser.add_option('-f', '--config-file', dest = 'config', \
#			  default = '.pymailheadersrc', help = 'configuration file path')
	parser.add_option('-g', '--geometry', dest = 'geometry', \
			  default = '400x100+0+0', \
			  help = 'geometry of the window')
	parser.add_option('--bg', dest = 'bg', default = 'black', \
			  help = 'backgound color')
	parser.add_option('--fg', dest = 'fg', default = 'green', \
			  help = 'foreground color')
	parser.add_option('--fgn', dest = 'fg_new', default = 'yellow', \
			  help = 'foreground color for new messages')
	(options, args) = parser.parse_args()

	# check args
	if options.server_type == None or options.server == None:
		parser.error('server type and server are required.')
	if options.auth and (options.username == '' or options.password == ''):
		parser.error('username and password are needed ' + \
			     'for authentication.')

	global lock
	global gui_thr
	global messages
	
	# create threads
	gui_thr = gui.gui(options.geometry, options.fg, \
			  options.bg, options.fg_new)
	geometry = int(re.search('x(\d+)', options.geometry).group(1)) / \
		   gui_thr.get_font_size()
	mail_thr = mail_thread(options.server_type, options.server, \
			       options.username, options.password, \
			       options.ssl, geometry, options.interval)

	# setup event handler
	def update_event_handler(event):
		global lock
		global messages
		global gui_thr

		lock.acquire()
		gui_thr.display(messages)
		lock.release()

	gui_thr.bind('<<Update>>', update_event_handler)

	try:
		# start thread
		mail_thr.start()
		gui_thr.mainloop()
	except KeyboardInterrupt:
		pass

	# stop mail thread
	mail_thr.timer.set()

	# clean up the mess
	del mail_thr
	del gui_thr
	
# rock n' roll
if __name__ == '__main__':
	main()
