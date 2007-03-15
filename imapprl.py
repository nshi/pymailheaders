#!/usr/bin/env python
#
# imapprl.py
# Copyright 2007 Neil Shi <zeegeek@gmail.com>
#
# IMAP Protocol
# This is the IMAP protocol support module for pymailheaders.
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

import imaplib
import socket
import re
from sys import stderr

from exception import *

class imap:
	"""imap class

	@attention: if an exception Exception is thrown by any of the method, by
		disconnecting and connecting again, the problem should be
		solved.

	@warning: B{Have to call connect() method before doing anything else}

	@note: Private member variables:
		__size
		__server
		__mbox
		__uname
		__pass
		__ssl
		__connection

	@note: Public member variables:
		new
	"""

	def __init__(self, server, uname, password, ssl, h, mbox):
		"""Constructor

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
		@type mbox: string
		@param mbox: mailbox.
		"""

		self.__server = server
		self.__mbox = mbox
		self.__uname = uname
		self.__pass = password
		self.__ssl = ssl
		self.__size = h
		self.new = 0

	def __del__(self):
		"""Destructor
		Should log out and destroy the connection.
		"""

		try:
			response = self.__connection.logout()
			if response[0] != 'BYE':
				print >> stderr, 'imapprl (__del__):', \
				      response[1]
				raise Exception('(__del__) ' + response[1])
		except (socket.error, socket.gaierror, imaplib.IMAP4.error,
			imaplib.IMAP4.abort), strerr:
			print >> stderr, 'imapprl (__del__):', strerr
			raise Exception(strerr)
		except:
			raise

	def __check(self):
		"""Check if the mailbox has new messages.

		@rtype: int
		@return: total number of messages
		"""

		try:
			response = self.__connection.status('INBOX', \
							    '(MESSAGES UNSEEN)')
			if response[0] != 'OK':
				print >> stderr, 'imapprl (__check):', \
				      response[1]
				raise Exception('(__check) ' + response[1])
		except (socket.error, socket.gaierror, imaplib.IMAP4.error,
			imaplib.IMAP4.abort), strerr:
			print >> stderr, 'imapprl (__check):', strerr
			raise Exception('(__check) ' + strerr)
		except:
			raise

		total_new = re.search('\D+(\d+)\D+(\d+)', \
				      response[1][0]).groups()
		self.new = int(total_new[1])
		return int(total_new[0])

	def __select_mailbox(self):
		"""Select a mailbox
		"""

		try:
			response = self.__connection.select(self.__mbox, True)
			if response[0] != 'OK':
				print >> stderr, 'imapprl (__select_mailbox):',\
				      response[1]
				raise Exception('(__select_mailbox) ' + \
						response[1])
		except (socket.error, socket.gaierror, imaplib.IMAP4.error,
			imaplib.IMAP4.abort), strerr:
			print >> stderr, 'imapprl (__select_mailbox):', strerr
			raise Exception('(__select_mailbox) ' + strerr)
		except:
			raise

	def connect(self):
		"""Connect to the server and log in.

		If the connection has already established, return.

		@attention: when exception TryAgain is thrown by this method,
			the calling program should try to connect again.
		
		@raise TryAgain: when network is temporarily unavailable
		"""

		try:
			if self.__ssl:
				self.__connection = imaplib.IMAP4_SSL( \
					self.__server)
			else:
				self.__connection = imaplib.IMAP4(self.__server)
			response = self.__connection.login(self.__uname,
							   self.__pass)
			if response[0] != 'OK':
				print >> stderr, 'imapprl (connect):', \
				      response[1]
				raise Exception('(connect) ' + response[1])
		except socket.gaierror, (socket.EAI_AGAIN, strerr):
			print >> stderr, 'imapprl (connect):', strerr
			raise TryAgain
		except (socket.error, socket.gaierror, imaplib.IMAP4.error), \
			strerr:
			print >> stderr, 'imapprl (connect):', strerr
			raise Exception('(connect) ' + strerr)
		except:
			raise

		# set socket timeout to 30 seconds
		self.__connection.socket().settimeout(10)

	def get_mail(self):
		"""Get mails.

		@rtype: list
		@return: List of tuples of sender addresses and subjects, newest
			message on top.
		"""

		try:
			num = self.__check()
			self.__select_mailbox()
			
			if self.__size < num:
				mail_list = self.__connection.fetch( \
					str(num - self.__size) + ':' + str(num), \
					'(UID BODY.PEEK[HEADER.FIELDS ' + \
					'(FROM SUBJECT)])')
			else:
				mail_list = self.__connection.fetch( \
					'1:' + str(num), \
					'(UID BODY.PEEK[HEADER.FIELDS ' + \
					'(FROM SUBJECT)])')
			if mail_list[0] != 'OK':
				print >> stderr, 'imapprl (get_mail):', \
				      response[1]
				raise Exception('(get_mail)' + response[1])

			response = self.__connection.close()
			if response[0] != 'OK':
				print >> stderr, 'imapprl (get_mail):', \
				      response[1]
				raise Exception('(get_mail) ' + response[1])
		except (socket.error, socket.gaierror, imaplib.IMAP4.error,
			imaplib.IMAP4.abort), strerr:
			print >> stderr, 'imapprl (get_mail):', strerr
			raise Exception('(get_mail) ' + strerr)
		except:
			raise

		# parse sender addresses and subjects
		def a(x): return x != ')'
		# ATTENTION: cannot rely on the order of the reply by fetch
		# command, it's arbitrary.
		def b(x): return (re.search('From: ([^\r\n]+)', \
					    x[1].strip()).group(1), \
				  re.search('Subject: ([^\r\n]+)', \
					    x[1].strip()).group(1))
		messages = map(b, filter(a, mail_list[1]))
		messages.reverse()
		return messages
