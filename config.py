#!/usr/bin/env python
#
# constants.py
# Copyright 2007 Neil Shi <zeegeek@gmail.com>
#
# Configuration File Parser
# This file contains the configuration parser for pymailheaders
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

from ConfigParser import *
from sys import stderr
import os.path

class config:
	"""This class parses and saves the configuration file for pymailheaders.

	@attention: Put all boolean variables names in __bool_vals so that we
	can return them in the right type later.
	
	@note: Private member variables:
		__section
		__defaults
		__bool_vals
		__int_vals
		__config_file
		__config
	"""

	__section = 'settings'

	__defaults = {'auth': False,
		      'encrypted': False,
		      'interval': 180,
		      # GUI settings
		      'height': 100,
		      'width': 400,
		      'x': 0,
		      'y': 0,
		      'background': 'black',
		      'foreground': 'green',
		      'foreground new': 'yellow',
		      'font': 'Simsun 12',
		      'border': 0,
		      'decorated': True,
		      'focus': True,
		      'top': False,
		      'pager': True,
		      'taskbar': True,
		      'sticky': False}

	# boolean options
	__bool_vals = ('auth',
		       'encrypted',
		       'decorated',
		       'focus',
		       'top',
		       'pager',
		       'taskbar',
		       'sticky')

	# integer options
	__int_vals = ('interval',
		      'height',
		      'width',
		      'x',
		      'y',
		      'border')

	# stores configuration filename
	__config_file = ''

	def __init__(self, filename):
		"""Constructor

		@type filename: string
		@param filename: full configuration file name
		"""

		self.__config = SafeConfigParser()
		self.__config_file = filename

		try:
			# if the file does not exist, create it and write
			# default values to it.
			if not os.path.isfile(self.__config_file):
				for k, v in self.__defaults.iteritems():
					self.set(k, v)
				self.write()

			# check if we have the correct permissions
			fd = open(self.__config_file, 'rw')
			fd.close()
				
			self.__config.read(self.__config_file)

			# Insert default values
			# I have to do this because ConfigParser will insert a
			# section called DEFAULT if I use the defaults method.
			for k, v in self.__defaults.iteritems():
				if not self.__has(k): self.set(k, v)
		except (IOError, ParsingError, MissingSectionHeaderError), \
			   strerr:
			print >> stderr, 'config (__init__):', strerr
			raise Exception('config (__init__): ' + str(strerr))
		except:
			raise

	def __del__(self):
		"""Destructor

		@note: make sure that changes are being written to the file.
		"""
		
		self.write()

		del self.__config

	def __has(self, opt):
		"""Determine if an option exists in the config file

		@type opt: string
		@param opt: option name
		@rtype: bool
		@return: True if it has the option, False otherwise.
		"""

		return self.__config.has_option(self.__section, opt)

	def set(self, opt, val):
		"""Set option's value to value

		@type opt: string
		@param opt: option name
		@type val: string or bool or int
		@param val: option's value
		"""

		try:
			if opt in self.__bool_vals:
				if type(val) != bool:
					raise TypeError
				
				if val:
					self.__config.set(self.__section, opt, \
							  'yes')
				else:
					self.__config.set(self.__section, opt, \
							  'no')
			elif opt in self.__int_vals:
				if type(val) != int:
					raise TypeError

				self.__config.set(self.__section, opt, str(val))
			elif type(val) == bool or type(val) == int:
				raise TypeError
			else:
				self.__config.set(self.__section, opt, val)
		except NoSectionError, strerr:
			print >> stderr, 'config (set):', strerr
			print >> stderr, 'config (set): creating...'

			# create section
			self.__config.add_section(self.__section)
			# try to add the option
			self.set(opt, val)
		except TypeError:
			print >> stderr, 'config (set):', 'invalid value type.'
			raise Exception('config (set): ' + 'invalid value type')
		except:
			raise

	def get(self, opt):
		"""Get option's value

		If the option has a boolean value, convert it into boolean type.
		If it's a integer value, convert it to integer type.

		@type opt: string
		@param opt: option name
		@rtype: string or bool or int
		@return: option's value
		"""

		try:
			if opt in self.__bool_vals:
				return self.__config.get(self.__section, opt).\
				       lower() == 'yes'
			elif opt in self.__int_vals:
				return int(self.__config.get(self.__section, \
							     opt))

			return self.__config.get(self.__section, opt)
		except (NoSectionError, \
			NoOptionError), strerr:
			print >> stderr, 'config (get):', strerr
			raise Exception('config (get): ' + str(strerr))

	def get_all(self):
		"""Get all options' values in the right type

		@rtype: dictionary
		@return: options' values
		"""

		optvals = {}
		
		try:
			opts = self.__config.options(self.__section)

			for k in opts:
				optvals[k] = self.get(k)
		except:
			raise

		return optvals

	def write(self):
		"""Write configurations to file
		"""

		try:
			# make sure that all options will be written into the
			# config file
			for k, v in self.__defaults.iteritems():
				if not self.__has(k): self.set(k, v)
				
			fd = open(self.__config_file, 'wU')

			self.__config.write(fd)

			fd.close()
		except IOError, strerr:
			print >> stderr, 'config (write):', strerr
			raise Exception('config (write): ' + str(strerr))
