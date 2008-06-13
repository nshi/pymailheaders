#!/usr/bin/env python
#
# popprl.py
# Copyright 2008 Neil Shi <zeegeek@gmail.com>
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
from email.Header import decode_header

import chardet
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
        @param h: dummy variable
        @type mbox: string
        @param mbox: dummy variable, POP3 only deals with INBOX.
        """

        self.__server = server
        self.__uname = uname
        self.__pass = password
        self.__ssl = ssl
        self.__message_dict = {}

    def __disconnect(self):
        """Destructor
        Should log out and destroy the connection.
        """

        try:
            response = self.__connection.quit()
            if response[0:3] != '+OK':
                raise Error('popprl (__disconnect)', _('Logout failed'))
        except (socket.error, socket.gaierror, poplib.error_proto,
                AttributeError), strerr:
            raise Error('popprl (__disconnect)', strerr)
        except:
            raise

    def __connect(self):
        """Connect to the server and log in.

        If the connection has already established, return.

        @attention: when exception TryAgain is thrown by this method,
        the calling program should try to connect again.

        @raise TryAgain: when network is temporarily unavailable
        """

        try:
            if self.__ssl:
                self.__connection = poplib.POP3_SSL(self.__server)
            else:
                self.__connection = poplib.POP3(self.__server)

            # Authentication: send username and password in clear
            # text.
            response = self.__connection.user(self.__uname)
            if response[0:3] != '+OK':
                raise Error('popprl (connect)', _('Login failed'))
            response = self.__connection.pass_(self.__pass)
            if response[0:3] != '+OK':
                raise Error('popprl (connect)', _('Login failed'))
        except socket.gaierror, (socket.EAI_AGAIN, strerr):
            raise TryAgain('popprl (connect)', strerr)
        except (socket.error, socket.gaierror, poplib.error_proto), strerr:
            raise Error('popprl (connect)', strerr)
        except:
            raise

    def connect(self):
        """Dummy function for compatibility reason.

        Since POP3 locks the maildrop once the user has been
        authenticated, we don't connect unless we're checking for new
        messages.
        """

        pass

    def get_mail(self):
        """Get mails.

        @rtype: list
        @return: List of tuples of flag, sender addresses and subjects.
        Newest message on top.
        """

        # Steps: 1. connect to the server;
        #        2. get the total number of messages in the mailbox;
        #        3. get message unique IDs and compare them with the
        #           ones stored in __message_dict, if they don't exist,
        #           count them as new messages and add them to
        #           __message_dict;
        #        4. get message headers;
        #        5. disconnect from server.

        header_list = []
        uid_list = []

        try:
            # 1. connect to the server
            self.__connect()

            # 2. get the total number of messages in the mailbox.
            # POP3 has no way of indicating how many new messages
            # there are.
            total = self.__connection.stat()[0]

            message_range = range(total, 0, -1)
            for i in message_range:
                # 3. get unique IDs
                response = self.__connection.uidl(i)
                if response[0:3] != '+OK':
                    raise Error('popprl (get_mail)', \
                                _('Fetching message ID failed'))
                uid = re.search('([\S]*)$', response).group(1)

                # compare unique IDs with the ones we've already
                # had
                if not self.__message_dict.has_key(uid):
                    flag = True
                else:
                    flag = False
                uid_list.append(uid)

                # 4. get message hearders
                response = self.__connection.top(i, 0)
                if response[0][0:3] != '+OK':
                    raise Error('popprl (get_mail)', \
                                _('Fetching messages failed'))

                # decode mime headers
                def d(x):
                    y = decode_header(x)
                    return ' '.join(s[1] and s[0].decode(s[1]) or s[0] for s in y)

                def b(x):
                    r = re.search('^(From|Subject)', x)
                    if r == None:
                        return False
                    else:
                        return True
                def c(x):
                    r = re.search('^(From|Subject):\s*(.*)', x).group(2)
                    return r
                # POP3 doesn't guarantee the order of header
                # fields returned, we'd have to determine it by
                # ourselves.
                filtered_header = filter(b, response[1])
                if re.search('^From', filtered_header[0]) == None:
                    filtered_header.reverse()
                header = map(c, filtered_header)
                # get sender's name if there's one, otherwise get the email
                # address
                (name, addr) = re.search('("?([^"]*)"?\s)?<?(([a-zA-Z0-9_\-\.])+@(([0-2]?[0-5]?[0-5]\.[0-2]?[0-5]?[0-5]\.[0-2]?[0-5]?[0-5]\.[0-2]?[0-5]?[0-5])|((([a-zA-Z0-9\-])+\.)+([a-zA-Z\-])+)))?>?', header[0]).groups()[1:3]
                header_list.append((flag, name and d(name) or \
                                    addr, d(header[1])))

            # 5. disconnect from server. Don't keep POP3 server
            # locking up the mailbox.
            self.__disconnect()
        except (socket.error, socket.gaierror, poplib.error_proto,), strerr:
            raise Error('popprl (get_mail)', strerr)
        except:
            raise

        # refresh __message_dict
        self.__message_dict.clear()
        self.__message_dict = self.__message_dict.fromkeys(uid_list, None)

        return header_list
