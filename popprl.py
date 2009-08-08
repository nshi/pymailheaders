#!/usr/bin/env python
#
# popprl.py
# Copyright 2009 Ning Shi <zeegeek@gmail.com>
#
# POP3 Protocol
# This is the POP3 protocol support module for pymailheaders.
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

import poplib
import socket
import re
import logging
from email import message_from_string
from email.utils import parseaddr, parsedate_tz, mktime_tz
from email.Header import decode_header
from datetime import datetime

from exception import *

class pop:
    """pop class

    @attention: if an exception Error is thrown by any of the method, by
    disconnecting and connecting again, the problem should be solved.

    @warning: B{Have to call connect() method before doing anything else}

    @note: Private member variables:
        __server
        __uname
        __pass
        __ssl
        __size
        __connection
        __message_dict
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
        @param h: number of messages displayable in the window
        @type mbox: string
        @param mbox: dummy variable, POP3 only deals with INBOX.
        """

        self.__server = server
        self.__uname = uname
        self.__pass = password
        self.__ssl = ssl
        self.__size = h
        self.__connection = None
        self.__message_dict = []
        self.__logger = logging.getLogger('pop')

    def __command(self, cmd, method_name, *args, **kwargs):
        """Run the POP3 command.

        @type cmd: string
        @param cmd: the POP3 command to run
        @type method_name: string
        @param method_name: the name of the method which called this method.
        @rtype: list
        @return: response from the POP3 command
        """

        try:
            response = getattr(self.__connection, cmd)(*args, **kwargs)
            if response[0:3] != '+OK':
                self.__logger.error(response[4:])
                raise Error('popprl (%s)' % method_name, response[4:])
        except socket.gaierror, (socket.EAI_AGAIN, strerr):
            self.__logger.error(str(strerr))
            raise TryAgain('popprl (%s)' % method_name, strerr)
        except (socket.error, socket.gaierror, poplib.error_proto), strerr:
            self.__logger.error(str(strerr))
            self.__disconnect()
            raise Error('popprl (%s)' % method_name, strerr)
        except:
            self.__disconnect()
            raise

    def __disconnect(self):
        """Destructor
        Should log out and destroy the connection.
        """

        self.__logger.debug('Destroy')

        if not self.__connection:
            return

        try:
            response = self.__connection.quit()
            if response[0:3] != '+OK':
                self.__logger.error('Failed to logout')
                raise Error('popprl (__disconnect)', _('Logout failed'))
        except (socket.error, socket.gaierror, poplib.error_proto,
                AttributeError), strerr:
            self.__logger.error(str(strerr))
            raise Error('popprl (__disconnect)', strerr)
        except:
            raise
        finally:
            self.__connection = None

    def __connect(self):
        """Connect to the server and log in.

        If the connection has already established, return.

        @attention: when exception TryAgain is thrown by this method,
        the calling program should try to connect again.

        @raise TryAgain: when network is temporarily unavailable
        """

        self.__logger.debug('Connect')

        if self.__connection:
            return

        try:
            if self.__ssl:
                self.__connection = poplib.POP3_SSL(self.__server)
            else:
                self.__connection = poplib.POP3(self.__server)

            # Authentication: send username and password in clear
            # text.
            self.__command('user', '__connect', self.__uname)
            self.__command('pass_', '__connect', self.__pass)
        except socket.gaierror, (socket.EAI_AGAIN, strerr):
            self.__logger.error(str(strerr))
            raise TryAgain('popprl (__connect)', strerr)
        except (socket.error, socket.gaierror, poplib.error_proto), strerr:
            self.__logger.error(str(strerr))
            self.__disconnect()
            raise Error('popprl (__connect)', strerr)
        except:
            self.__disconnect()
            raise

    def get_mail(self):
        """Get mails.

        @rtype: tuple
        @return: the tuple is in the following form
        ([(datetime, sender, subject), ...],    <--- unread mails
         [(datetime, sender, subject), ...])    <--- read mails
        """

        # Steps: 1. connect to the server;
        #        2. get the total number of messages in the mailbox;
        #        3. get message unique IDs and compare them with the
        #           ones stored in __message_dict, if they don't exist,
        #           count them as new messages and add them to
        #           __message_dict;
        #        4. get message headers;
        #        5. disconnect from server.

        messages = ([], [])

        self.__logger.debug('Get mail')

        # 1. connect to the server
        self.__connect()

        # 2. get the total number of messages in the mailbox.
        # POP3 has no way of indicating how many new messages
        # there are.
        total = self.__command('stat', 'get_mail')[0]

        message_range = range(total, 0, -1)
        for i in message_range:
            # if the number of messages reaches the displayable max, stop
            if (len(messages[0]) + len(messages[1])) == self.__size:
                break

            # 3. get unique IDs
            response = self.__command('uidl', 'get_mail', i)
            uid = re.search('([\S]*)$', response).group(1)

            # 4. get message hearders
            response = self.__command('top', 'get_mail', i, 0)

            # 5. disconnect from server. Don't keep POP3 server
            # locking up the mailbox.
            self.__disconnect()

            def d(x):
                # In case the string is not compliant with the standard,
                # let's make it correct.
                try:
                    y = decode_header(re.sub(r'(=\?([^\?]*\?){3}=)',
                                             r' \1 ', x))
                    res = ''.join(s[1] and s[0].decode(s[1]) or
                                  s[0] for s in y)
                    # Strips multiple contiguous white spaces into one.
                    res = ' '.join(res.split())
                    return res
                except UnicodeDecodeError:
                    self.__logger.error('Invalid encoding')
                    raise Error('popprl (get_mail)', _('Invalid encoding'))

            def b(x):
                r = re.search('^(From|Subject|Date)', x)
                if r == None:
                    return False
                else:
                    return True

            filtered_header = filter(b, response[1])
            msg = message_from_string('\r\n'.join(filtered_header))
            subject = d(msg['subject'])
            (sender, addr) = parseaddr(msg['from'])
            sender = sender and d(sender) or addr
            date = parsedate_tz(msg['date'])
            dt = date and datetime.fromtimestamp(mktime_tz(date)) or \
                datetime.now()

            if uid in self.__message_dict:
                # old message
                messages[1].append((dt, sender, subject))
            else:
                # new message
                messages[0].append((dt, sender, subject))
                self.__message_dict.append(uid)

        return messages
