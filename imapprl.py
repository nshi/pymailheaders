#!/usr/bin/env python
#
# imapprl.py
# Copyright 2009 Ning Shi <zeegeek@gmail.com>
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
import logging
from email import message_from_string
from email.utils import parseaddr, parsedate_tz, mktime_tz
from email.Header import decode_header
from datetime import datetime

import chardet
from exception import *

class imap:
    """imap class

    @attention: if an exception Error is thrown by any of the method, by
    disconnecting and connecting again, the problem should be solved.

    @warning: B{Have to call connect() method before doing anything else}

    @note: Private member variables:
        __TIMEOUT
        __server
        __mbox
        __uname
        __pass
        __ssl
        __connection
        __size
    """

    __TIMEOUT = 20

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
        @param mbox: mailbox.
        """

        self.__server = server
        self.__mbox = mbox
        self.__uname = uname
        self.__pass = password
        self.__ssl = ssl
        self.__size = h
        self.__connection = None
        self.__logger = logging.getLogger('imap')

    def __del__(self):
        """Destructor
        Should log out and destroy the connection.
        """

        self.__logger.debug('Destroy')
        self.__disconnect()

    def __check(self):
        """Get the total number and the number of new messages in a mailbox.

        @rtype: tuple
        @return: (total number of messages, number of new messages)
        """

        self.__logger.debug('Check for new mails')

        try:
            response = self.__connection.status('INBOX', '(MESSAGES UNSEEN)')
            if response[0] != 'OK':
                self.__logger.error(response[1])
                raise Error('imapprl (__check)', response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
                imaplib.IMAP4.abort), strerr:
            self.__logger.error(str(strerr))
            self.__disconnect()
            raise Error('imapprl (__check)', str(strerr))
        except:
            self.__disconnect()
            raise

        num = re.search('\D+(\d+)\D+(\d+)', response[1][0]).groups()
        return (int(num[0]), int(num[1]))

    def __select_mailbox(self):
        """Select a mailbox
        """

        self.__logger.debug('Select mailbox')

        try:
            response = self.__connection.select(self.__mbox, True)
            if response[0] != 'OK':
                self.__logger.error(response[1])
                raise Error('imapprl (__select_mailbox)', response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
                imaplib.IMAP4.abort), strerr:
            self.__logger.error(str(strerr))
            self.__disconnect()
            raise Error('imapprl (__select_mailbox)', str(strerr))
        except:
            self.__disconnect()
            raise

    def __connect(self):
        """Connect to the server and log in.

        If the connection has already established, return.

        @attention: when exception TryAgain is thrown by this method,
        the calling program should try to connect again.

        @raise TryAgain: when network is temporarily unavailable.
        """

        self.__logger.debug('Connect')

        try:
            if self.__ssl:
                self.__connection = imaplib.IMAP4_SSL(self.__server)
            else:
                self.__connection = imaplib.IMAP4(self.__server)
            self.__connection.socket().settimeout(self.__class__.__TIMEOUT)

            response = self.__connection.login(self.__uname, self.__pass)
            if response[0] != 'OK':
                self.__logger.error(response[1])
                raise Error('imapprl (connect)', response[1])
        except socket.gaierror, (socket.EAI_AGAIN, strerr):
            self.__logger.error(str(strerr))
            raise TryAgain('imapprl (connect)', strerr)
        except (socket.error, socket.gaierror, imaplib.IMAP4.error), strerr:
            self.__logger.error(str(strerr))
            raise Error('imapprl (connect)', str(strerr))
        except:
            raise

    def __disconnect(self):
        """Disconnect from the server.

        If the connection has not been established, return.

        @raise Error: when error occurs.
        """

        try:
            if not self.__connection:
                return

            response = self.__connection.logout()
            if response[0] != 'BYE':
                self.__logger.error(response[1])
                raise Error('imapprl (__disconnect)', response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
                imaplib.IMAP4.abort), strerr:
            self.__logger.error(str(strerr))
            raise Error('imapprl (__disconnect)', str(strerr))
        except:
            raise

        self.__connection = None

    def get_mail(self):
        """Get mails.

        @rtype: tuple
        @return: the tuple is in the following form
        ([(datetime, sender, subject), ...],    <--- unread mails
         [(datetime, sender, subject), ...])    <--- read mails
        """

        if not self.__connection:
            self.__connect()

        messages = ([], [])

        self.__logger.debug('Get mail')

        try:
            num = self.__check()
            self.__select_mailbox()

            # if the number of new messages is more than what the window can
            # hold, get them all.  Otherwise, fill up the whole window with old
            # messages at the bottom.
            if self.__size < num[1]:
                num_to_fetch = str(num[0] - num[1])
            else:
                num_to_fetch = str(num[0] < self.__size and 1
                                   or num[0] - self.__size)
            mail_list = self.__connection.fetch(num_to_fetch + ':' +
                                                str(num[0]), '(FLAGS BODY.PEEK'
                                                + '[HEADER.FIELDS '
                                                + '(DATE FROM SUBJECT)])')
            if mail_list[0] != 'OK':
                self.__logger.error(response[1])
                raise Error('imapprl (get_mail)', response[1])

            response = self.__connection.close()
            if response[0] != 'OK':
                self.__logger.error(response[1])
                raise Error('imapprl (get_mail)', response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
                imaplib.IMAP4.abort), strerr:
            self.__logger.error(str(strerr))
            raise Error('imapprl (get_mail)', str(strerr))
        except:
            raise

        def d(x):
            # In case the string is not compliant with the standard, let's make
            # it correct.
            try:
                y = decode_header(re.sub(r'(=\?([^\?]*\?){3}=)', r' \1 ', x))
                res = ''.join(s[1] and s[0].decode(s[1]) or s[0] for s in y)
                # Strips multiple contiguous white spaces into one.
                res = ' '.join(res.split())
                return res
            except UnicodeDecodeError:
                self.__logger.error('Invalid encoding')
                raise Error('imapprl (get_mail)', _('Invalid encoding'))

        def a(x): return x != ')'

        results = filter(a, mail_list[1])
        for header in results:
            msg = message_from_string(header[1])
            flags = imaplib.ParseFlags(header[0])
            subject = d(msg['subject'])
            (sender, addr) = parseaddr(msg['from'])
            sender = sender and d(sender) or addr
            date = parsedate_tz(msg['date'])
            dt = date and datetime.fromtimestamp(mktime_tz(date)) or \
                datetime.now()

            if '\\Deleted' in flags:
                continue

            if '\\Seen' in flags:
                messages[1].append((dt, sender, subject))
            else:
                messages[0].append((dt, sender, subject))

        messages[0].reverse()
        messages[1].reverse()

        self.__disconnect()

        return messages
