#!/usr/bin/env python
#
# config.py
# Copyright 2009 Ning Shi <zeegeek@gmail.com>
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
import os
import os.path

from exception import *

class config:
    """This class parses and saves the configuration file for pymailheaders.

    @attention: Put all boolean variables names in __bool_vals so that we
    can return them in the right type later.

    @note: Private member variables:
        __section
        __acct_opts
        __defaults
        __bool_vals
        __int_vals
        __config_file
        __config
    """

    __acct_opts = ('type',
                   'server',
                   'username',
                   'password',
                   'auth',
                   'encrypted',
                   'interval')

    __defaults = {'type': None,
                  'server': '',
                  'username': '',
                  'password': '',
                  'auth': False,
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
        self.__section = 'settings'

        try:
            # if the file does not exist, create it and write
            # default values to it.
            if not os.path.isfile(self.__config_file):
                for k, v in self.__class__.__defaults.iteritems():
                    if k not in self.__class__.__acct_opts:
                        self.set(k, v)
                self.write()

            # check if we have the correct permissions
            fd = open(self.__config_file, 'rw')
            fd.close()

            self.__config.read(self.__config_file)

            # Insert default values
            # I have to do this because ConfigParser will insert a
            # section called DEFAULT if I use the defaults method.
            for k, v in self.__class__.__defaults.iteritems():
                if k not in self.__class__.__acct_opts and not self.__has(k):
                    self.set(k, v)
        except (IOError, ParsingError, MissingSectionHeaderError), strerr:
            raise Error('config (__init__)', str(strerr))
        except:
            raise

    def __del__(self):
        """Destructor

        @note: make sure that changes are being written to the file.
        """

        self.write()

    def __has(self, opt, acct = None):
        """Determine if an option exists in the config file

        @type opt: string
        @param opt: option name
        @type acct: string
        @param acct: account name
        @rtype: bool
        @return: True if it has the option, False otherwise.
        """

        if acct is None:
            acct = self.__section

        return self.__config.has_option(acct, opt)

    def make_empty_acct(self):
        """Generates an empty account with default settings.

        @rtype: dictionary
        @return: An empty account.
        """

        res = {}
        for k in self.__class__.__acct_opts:
            res[k] = self.__class__.__defaults[k]
        return res

    def remove_account(self, acct):
        """Removes an account

        @type acct: string
        @param acct: account name
        """

        self.__config.remove_section(acct)

    def remove_option(self, opt, acct = None):
        """Removes an option from an account

        @type opt: string
        @param opt: option name
        @type acct: string
        @param acct: account name
        """

        if acct is None:
            acct = self.__section

        try:
            self.__config.remove_option(acct, opt)
        except NoSectionError, strerr:
            raise Error('config (remove_option)', _('invalid account name'))

    def set(self, opt, val, acct = None):
        """Set option's value to value

        @type opt: string
        @param opt: option name
        @type val: string or bool or int
        @param val: option's value
        @type acct: string
        @param acct: account name
        """

        if acct is None:
            acct = self.__section

        try:
            # convert from boolean values
            if opt in self.__class__.__bool_vals:
                if type(val) != bool:
                    raise TypeError

                if val:
                    self.__config.set(acct, opt, 'yes')
                else:
                    self.__config.set(acct, opt, 'no')
            # convert from integers
            elif opt in self.__class__.__int_vals:
                if type(val) != int:
                    raise TypeError

                self.__config.set(acct, opt, str(val))
            elif type(val) == bool or type(val) == int:
                raise TypeError
            else:
                self.__config.set(acct, opt, val)
        except NoSectionError, strerr:
            print >> stderr, 'config (set):', strerr
            print >> stderr, 'config (set): creating...'

            # create section
            self.__config.add_section(acct)
            # try to add the option
            self.set(opt, val, acct)
        except TypeError:
            raise Error('config (set)', _('invalid value type'))
        except:
            raise

    def get(self, opt, acct = None):
        """Get option's value

        If the option has a boolean value, convert it into boolean type.
        If it's a integer value, convert it to integer type.

        If you want to migrate the old style config file to the new format, use
        get_all method.

        @type opt: string
        @param opt: option name
        @type acct: string
        @param acct: account name
        @rtype: string or bool or int
        @return: option's value
        """

        if acct is None:
            acct = self.__section

        try:
            # convert to boolean values
            if opt in self.__class__.__bool_vals:
                return self.__config.getboolean(acct, opt)
            # convert to integers
            elif opt in self.__class__.__int_vals:
                return self.__config.getint(acct, opt)

            return self.__config.get(acct, opt)
        except (NoSectionError, NoOptionError, ValueError), strerr:
            raise Error('config (get)', str(strerr))

    def get_all(self):
        """Get all options' values in the right type.

        Only this method migrates the old style config file to the new format.

        @rtype: dictionary
        @return: options' values stored in 'global' for GUI settings, account
        settings are stored in 'accounts' as accounts' dict.
        """

        optvals = {'accounts': {}}

        try:
            secs = self.__config.sections()
            for sec in secs:
                opts = self.__config.options(sec)

                for k in opts:
                    if k in self.__class__.__acct_opts:
                        # migrate old config file to the new format
                        old_sec = None
                        if sec == self.__section:
                            old_sec = sec
                            sec = 'account 1'
                            self.set(k, self.get(k), sec)
                            self.remove_option(k)

                        if sec not in optvals['accounts']:
                            optvals['accounts'][sec] = {}
                        optvals['accounts'][sec][k] = self.get(k, sec)

                        # restore the section name we set earlier
                        if old_sec:
                            sec = old_sec
                            old_sec = None
                    else:
                        optvals[k] = self.get(k, sec)
        except:
            raise

        return optvals

    def write(self):
        """Write configurations to file
        """

        try:
            # make sure that all options will be written into the
            # config file
            for k, v in self.__class__.__defaults.iteritems():
                if k not in self.__class__.__acct_opts and not self.__has(k):
                    self.set(k, v)

            fd = open(self.__config_file, 'w')

            self.__config.write(fd)

            fd.close()

            # Set file permission bits to 0600
            os.chmod(self.__config_file, 0600)

        except IOError, strerr:
            raise Error('config (write)', str(strerr))
