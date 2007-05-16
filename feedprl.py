#!/usr/bin/env python
#
# feedprl.py
# Copyright 2007 Neil Shi <zeegeek@gmail.com>
#
# Feed Protocol
# This is the xml feed protocol support module for pymailheaders.
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

import feedparser
import re
from sys import stderr

from exception import *

class feed:
    """feed class

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
        __url
        __feed
    """


    __server = ''
    __mbox = ''
    __uname = ''
    __pass = ''
    __ssl = False
    __url = ''
    __feed = {}

    def __init__(self, server, uname, password, ssl, h, mbox):
        """Constructor

        @type server: string
        @param server: feed URL
        @type uname: string
        @param uname: username
        @type password: string
        @param password: password
        @type ssl: bool
        @param ssl: dummy variable for compatibility
        @type h: int
        @param h: dummy variable
        @type mbox: string
        @param mbox: Gmail label
        """

        if server == 'gmail':
            self.__server = 'mail.google.com/gmail/feed/atom'
            self.__ssl = True
        else:
            # get rid of 'http[s]://'
            self.__server = re.sub('^[^/]*:/*', '', server)
            if ssl != None:
                self.__ssl = ssl
        if mbox != 'INBOX':
            self.__mbox = mbox
        # replace @ to html code
        if uname and password:
            self.__uname = uname.replace('@', '%40')
            self.__pass = password

    def connect(self):
        """Form URL.
        """

        # assemble URL
        if self.__ssl:
            self.__url = 'https://'
        else:
            self.__url = 'http://'
        if self.__uname and self.__pass:
            self.__url += self.__uname + ':' + self.__pass + '@'
        self.__url += self.__server

    def get_mail(self):
        """Parse feed.

        @rtype: list
        @return: List of tuples of flag, sender addresses and subjects.
                 Oldest message on top.
        """

        # get feed
        try:
            self.__feed = feedparser.parse(self.__url)
            # check if it's a well formed feed
            if self.__feed.bozo == 1 and \
                   not isinstance(self.__feed.bozo_exception, \
                                  feedparser.CharacterEncodingOverride) and \
                   not isinstance(self.__feed.bozo_exception, \
                                  feedparser.NonXMLContentType):
                a = self.__feed.bozo_exception
                print a
                raise Exception(hasattr(a, 'getMessage') and a.getMessage() or \
                                a)
        except:
            raise
        
        # parse sender addresses and subjects
        def a(x):
            sender = ''
            
            if x.has_key('author_detail'):
                author = x.author_detail
                if author.has_key('name'):
                    sender = author.name
                elif author.has_key('email'):
                    sender = author.email
            elif x.has_key('author'):
                sender = x.author
            return (True, sender, x.title)
        
        return map(a, self.__feed.entries)
