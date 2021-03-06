#!/usr/bin/env python
#
# feedprl.py
# Copyright 2009 Ning Shi <zeegeek@gmail.com>
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
import logging
from time import mktime
from datetime import datetime
from urllib2 import URLError

from exception import *

class feed:
    """feed class

    @attention: if an exception Error is thrown by any of the method, by
    disconnecting and connecting again, the problem should be solved.

    @note: Private member variables:
        __server
        __mbox
        __uname
        __pass
        __ssl
        __size
        __url
        __feed
    """

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
        @param h: number of messages displayable in the window
        @type mbox: string
        @param mbox: Gmail label
        """

        if server == 'gmail':
            self.__server = 'mail.google.com/gmail/feed/atom'
            self.__ssl = True
        else:
            # get rid of 'http[s]://'
            self.__server = re.sub('^[^/]*:/*', '', server)
            if ssl:
                self.__ssl = True
            else:
                self.__ssl = False
        # replace @ with html code
        self.__uname = uname.replace('@', '%40')
        self.__pass = password
        self.__size = h
        self.__mbox = mbox
        self.__url = ''
        self.__feed = {}
        self.__logger = logging.getLogger('feed')

    def __connect(self):
        """Form URL.
        """

        self.__logger.debug('Connect')

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

        @rtype: tuple
        @return: the tuple is in the following form
        ([(datetime, sender, subject), ...],    <--- unread mails
         [(datetime, sender, subject), ...])    <--- read mails
        """

        if not self.__url:
            self.__connect()

        self.__logger.debug('Get mail')

        # get feed
        try:
            e = None
            if 'etag' in self.__feed:
                e = self.__feed.etag
            m = None
            if 'modified' in self.__feed:
                m = self.__feed.modified
            self.__logger.info('parsing %s', self.__url)
            self.__feed = feedparser.parse(self.__url, etag = e, modified = m)

            if 'status' in self.__feed and self.__feed.status == 304:
                self.__logger.info('Feed has not changed since last check')

            # check if it's a well formed feed
            if self.__feed.bozo == 1 and \
                    not isinstance(self.__feed.bozo_exception,
                                   feedparser.CharacterEncodingOverride) and \
                                   not isinstance(self.__feed.bozo_exception,
                                                  feedparser.NonXMLContentType):
                a = self.__feed.bozo_exception

                if isinstance(a, URLError):
                    self.__logger.error(a.args)
                    raise TryAgain('feedprl (get_mail)', a.args)
                else:
                    strerr = hasattr(a, 'getMessage') and a.getMessage() or \
                        a.strerror

                    self.__logger.error(strerr)
                    raise Error('feedprl (get_mail)', strerr)
        except:
            self.__logger.error('Failed parsing feed: %s', repr(self.__feed))
            self.__feed = {}
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

            if x.has_key('updated_parsed'):
                date = x.updated_parsed
            else:
                date = x.published_parsed
            return (datetime.fromtimestamp(mktime(date)), sender, x.title)

        messages = map(a, self.__feed.entries)
        messages.sort(lambda x, y: cmp(x[0], y[0]), reverse = True)
        return (messages[:self.__size], [])
