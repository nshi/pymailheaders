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
        __server
        __mbox
        __uname
        __pass
        __ssl
        __connection
        __size
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
        @param mbox: mailbox.
        """

        self.__server = server
        self.__mbox = mbox
        self.__uname = uname
        self.__pass = password
        self.__ssl = ssl
        self.__size = h

    def __del__(self):
        """Destructor
        Should log out and destroy the connection.
        """

        try:
            response = self.__connection.logout()
            if response[0] != 'BYE':
                print >> stderr, 'imapprl (__del__):', response[1]
                raise Exception('imapprl (__del__): ' + response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
                imaplib.IMAP4.abort), strerr:
            print >> stderr, 'imapprl (__del__):', strerr
            raise Exception('imapprl (__del__): ' + str(strerr))
        except:
            raise

    def __check(self):
        """Get the total number and the number of new messages in a mailbox.

        @rtype: tuple
        @return: (total number of messages, number of new messages)
        """

        try:
            response = self.__connection.status('INBOX', '(MESSAGES UNSEEN)')
            if response[0] != 'OK':
                print >> stderr, 'imapprl (__check):', response[1]
                raise Exception('imapprl (__check): ' + response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
                imaplib.IMAP4.abort), strerr:
            print >> stderr, 'imapprl (__check):', strerr
            raise Exception('imapprl (__check): ' + str(strerr))
        except:
            raise

        num = re.search('\D+(\d+)\D+(\d+)', response[1][0]).groups()
        return (int(num[0]), int(num[1]))

    def __select_mailbox(self):
        """Select a mailbox
        """

        try:
            response = self.__connection.select(self.__mbox, True)
            if response[0] != 'OK':
                print >> stderr, 'imapprl (__select_mailbox):', response[1]
                raise Exception('imapprl (__select_mailbox): ' + response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
            imaplib.IMAP4.abort), strerr:
            print >> stderr, 'imapprl (__select_mailbox):', strerr
            raise Exception('imapprl (__select_mailbox): ' + str(strerr))
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
                self.__connection = imaplib.IMAP4_SSL(self.__server)
            else:
                self.__connection = imaplib.IMAP4(self.__server)
            response = self.__connection.login(self.__uname, self.__pass)
            if response[0] != 'OK':
                print >> stderr, 'imapprl (connect):', response[1]
                raise Exception('imapprl (connect): ' + response[1])
        except socket.gaierror, (socket.EAI_AGAIN, strerr):
            print >> stderr, 'imapprl (connect):', strerr
            raise TryAgain
        except (socket.error, socket.gaierror, imaplib.IMAP4.error), strerr:
            print >> stderr, 'imapprl (connect):', strerr
            raise Exception('imapprl (connect): ' + str(strerr))
        except:
            raise

    def get_mail(self):
        """Get mails.

        @rtype: list
        @return: List of tuples of flag, sender addresses and subjects.
        newest message on top.

            @note: flag I{B{True}} for new messages
        """

        try:
            num = self.__check()
            self.__select_mailbox()

            # if the number of new messages is more than what the window can
            # hold, get them all.  Otherwise, fill up the whole window with old
            # messages at the bottom.
            if self.__size < num[1]:
                num_to_fetch = str(num[0] - num[1])
            else:
                num_to_fetch = str(num[0] < self.__size and 1 \
                                   or num[0] - self.__size)
            mail_list = self.__connection.fetch(num_to_fetch + ':' + \
                                                str(num[0]), '(FLAGS BODY.PEEK' \
                                                + '[HEADER.FIELDS ' \
                                                + '(FROM SUBJECT)])')
            if mail_list[0] != 'OK':
                print >> stderr, 'imapprl (get_mail):', response[1]
                raise Exception('imapprl (get_mail) ' + response[1])

            response = self.__connection.close()
            if response[0] != 'OK':
                print >> stderr, 'imapprl (get_mail):', response[1]
                raise Exception('imapprl (get_mail) ' + response[1])
        except (socket.error, socket.gaierror, imaplib.IMAP4.error,
                imaplib.IMAP4.abort), strerr:
            print >> stderr, 'imapprl (get_mail):', strerr
            raise Exception('imapprl (get_mail): ' + str(strerr))
        except:
            raise

        # parse sender addresses and subjects
        def a(x): return x != ')'
        # ATTENTION: cannot rely on the order of the reply by fetch
        # command, it's arbitrary.
        def b(x):
            sender = re.search('From: ([^\r\n]+)', x[1].strip()).group(1)
            # get sender's name if there's one, otherwise get the email address
            (name, addr) = re.search('("?([^"]*)"?\s)?<?(([a-zA-Z0-9_\-\.])+@(([0-2]?[0-5]?[0-5]\.[0-2]?[0-5]?[0-5]\.[0-2]?[0-5]?[0-5]\.[0-2]?[0-5]?[0-5])|((([a-zA-Z0-9\-])+\.)+([a-zA-Z\-])+)))?>?', sender).groups()[1:3]
            subject =  re.search('Subject: ([^\r\n]+)', x[1].strip())
            # subject might be empty
            if subject == None:
                subject = ''
            else:
                subject = subject.group(1)
            # ATTENTION: some mail agents will clear all the flags to indicate
            # that a message is unread
            return (re.search('FLAGS \(.*\\Seen.*\)', \
                              x[0].strip()) == None, \
                    name and name or addr, subject)
        messages = map(b, filter(a, mail_list[1]))
        messages.reverse()
        return messages
