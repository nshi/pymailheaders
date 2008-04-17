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
import os
import os.path
import signal

import gui
import imapprl
import popprl
import feedprl
import config
import constants
from exception import *

# switch to the directory where this file resides in, so that it can find the
# glade file
CWD = os.getcwd()
basedir = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(os.path.join(basedir, '%s.py' % constants.NAME.lower())):
    if os.path.exists(os.path.join(os.getcwd(), '%s.py' % constants.NAME.lower())):
        basedir = os.getcwd()
sys.path.insert(0, basedir)
os.chdir(basedir)

# global varibals
mail_thr = None
gui_thr = None
conf = None

lock = Lock()
messages = []

JOIN_TIMEOUT = 1.0

class mail_thread(Thread):
    """This class creates the thread for fetching messages.

    @note: Public member variables:
        timer
    @note: Private member variables:
        __interval
        __mail_obj
    """

    def __init__(self, t, server, uname, password, ssl, h, interval, \
             mbox = 'INBOX'):
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
        @param h: number of messages displayable in the window
        @type interval: int
        @param interval: time interval between updates
        @type mbox: string
        @param mbox: mailbox.
            I{Default = 'INBOX'}
        """

        Thread.__init__(self, None, None, 'mail-thread', (), {})
        self.setDaemon(True)

        self.__interval = float(interval)
        if not globals().has_key('%sprl' % t):
            print >> sys.stderr, 'pymailheaders: unknown server type'
            sys.exit(1)
        self.__mail_obj = getattr(globals()['%sprl' % t], t)(server, \
                                                             uname, \
                                                             password, \
                                                             ssl, \
                                                             h, \
                                                             mbox)
        self.__connected = False
        self.timer = Event()

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
            messages = [(True, 'Error', str(strerr))]
            lock.release()
            self.connect()

    def connect(self):
        """Connect to the server.
        """

        global messages
        global lock

        try:
            self.__mail_obj.connect()
            self.__connected = True
        except TryAgain:
            self.__connected = False
            lock.acquire()
            messages = [(True, 'Error', 'Network not available')]
            lock.release()
        except Exception, strerr:
            self.__connected = False
            lock.acquire()
            messages = [(True, 'Error', str(strerr))]
            lock.release()

    def refresh(self):
        """Fetches mail and updates the GUI.
        """

        if not self.__connected:
                self.connect()
        if self.__connected:
                self.fetch()

        gui.gobject.idle_add(update_gui)

    def run(self):
        """Connect to the server and fetch for the first time
        """

        while not self.timer.isSet():
            self.refresh()
            self.timer.wait(self.__interval)

# update GUI
def update_gui():
    global lock
    global messages
    global gui_thr

    lock.acquire()
    gui_thr.display(messages)
    lock.release()

def on_refresh_activate():
    global mail_thr

    mail_thr.refresh()

def on_account_changed(opts):
    global mail_thr

    delete_mail_thr()
    new_mail_thr(opts)
    mail_thr.start()

def on_config_save(opts):
    global conf

    if type(opts) != dict:
        return

    # write settings to config file
    for k, v in opts.iteritems():
        conf.set(k, v)
    conf.write()

def on_exit(signum = None, frame = None):
    gui.gtk.quit()

def new_mail_thr(opts):
    global mail_thr
    global gui_thr

    if type(opts) != dict or mail_thr != None:
        return

    h = opts['height'] / gui_thr.get_font_size()
    mail_thr = mail_thread(opts['type'], opts['server'], \
                           opts['username'], opts['password'], \
                           opts['encrypted'], h, opts['interval'])

def delete_mail_thr():
    global mail_thr

    # stop mail thread
    mail_thr.timer.set()
    mail_thr.join(JOIN_TIMEOUT)

    # clean up the mess
    mail_thr = None

def is_posix():
    if sys.platform == 'win32':
        return False
    elif sys.platform == 'win64':
        return False
    else:
        return True

def main():
    """Main function
    """

    global lock
    global conf
    global gui_thr
    global mail_thr
    global messages

    # parse command-line arguments
    usage = 'usage: %prog [options]... args...'
    parser = OptionParser(usage)
    parser.add_option('-t', '--type', dest = 'type', default = '', \
                      help = 'server type: imap, pop, feed')
    parser.add_option('-s', '--server', dest = 'server', default = '', \
                      help = 'server to connect to')
    parser.add_option('-a', '--auth', action='store_true', dest = 'auth', \
                      help = 'server requires authentication')
    parser.add_option('-u', '--username', dest = 'username', default = '', \
                      help = 'username to log onto the server')
    parser.add_option('-p', '--password', dest = 'password', default = '', \
                      help = 'password')
    parser.add_option('-e', '--ssl', action = 'store_true', \
                      dest = 'encrypted', help = 'user SSL for the server')
    parser.add_option('-i', '--interval', dest = 'interval', type = 'int', \
                      help = 'update interval in seconds')
    parser.add_option('-c', '--config-file', dest = 'config', \
                      help = 'configuration file path')
    parser.add_option('-w', '--width', dest = 'width', type = 'int', \
                      help = 'width of the window')
    parser.add_option('-g', '--height', dest = 'height', type = 'int', \
                      help = 'height of the window')
    parser.add_option('--bg', dest = 'background', help = 'backgound color')
    parser.add_option('--fg', dest = 'foreground', \
                      help = 'foreground color')
    parser.add_option('--fgn', dest = 'foreground new', \
                      help = 'foreground color for new messages')
    (options, args) = parser.parse_args()

    if options.config:
        exp_path = os.path.expanduser(options.config)
        config_file = os.path.isabs(exp_path) and exp_path or \
                      os.path.join(CWD, exp_path)
    else:
        # default config file location
        if is_posix():
            config_file = os.path.expanduser('~/.pymailheadersrc')
        else:
            config_file = 'config.ini'

    try:
        # read in config file if there is any
        conf = config.config(config_file)
    except:
        sys.exit(1)

    # get all configurations
    #
    # command line arguments have higher priorities, so they can overwrite
    # config file options
    opts = conf.get_all()

    # this is way too ugly, it's not a proper use of optparse, but had to
    # use this hack to get arround.
    options = options.__dict__.copy()
    del options['config']

    # don't use opts.update() because that will write all None values
    for k in options.iterkeys():
        if not opts.has_key(k) or options[k]:
            opts[k] = options[k]

    # check args
    if not opts['type'] or not opts['server']:
        parser.error('server type and server are required.')
    if opts['auth'] and (not opts['username'] or not opts['password']):
        parser.error('username and password are needed ' + \
                 'for authentication.')

    # setup signal handler so that settings will be saved even if the
    # process is killed
    signal.signal(signal.SIGTERM, on_exit)

    # create threads
    gui_thr = gui.gui(opts)
    new_mail_thr(opts)

    # set up signal handlers
    handlers = {'on_refresh_activate': on_refresh_activate,
                'on_config_save': on_config_save,
                'on_account_changed': on_account_changed}
    gui_thr.signal_autoconnect(handlers)

    try:
        # start thread
        mail_thr.start()
        gui.gtk.gdk.threads_enter()
        gui.gtk.main()
        gui.gtk.gdk.threads_leave()
    except KeyboardInterrupt:
        pass

    delete_mail_thr()

# rock n' roll
if __name__ == '__main__':
    main()
