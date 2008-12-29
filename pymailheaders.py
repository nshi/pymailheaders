#!/usr/bin/env python
#
# pymailheaders.py
# Copyright 2008 Neil Shi <zeegeek@gmail.com>
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
from datetime import datetime
import sys
import re
import os
import os.path
import locale
import gettext
import logging

# switch to the directory where this file resides in, so that it can find the
# glade file
app_name = 'pymailheaders'
cwd = os.getcwd()
basedir = os.path.dirname(os.path.realpath(__file__))
if not os.path.exists(os.path.join(basedir, '%s.py' % app_name.lower())):
    if os.path.exists(os.path.join(cwd, '%s.py' % app_name.lower())):
        basedir = cwd
sys.path.insert(0, basedir)
os.chdir(basedir)

# set to default locale
locale.setlocale(locale.LC_ALL, '')

# load translation file
gettext.bindtextdomain(app_name, 'po')
gettext.textdomain(app_name)
import __builtin__
__builtin__._ = lambda x: x
try:
    locales = locale.getdefaultlocale()
    if locales[0]:
        trans = gettext.translation(app_name, 'po', [locales[0]])
        if trans:
            __builtin__._ = trans.ugettext
except IOError:
    pass

import signal
import gui
import imapprl
import popprl
import feedprl
import config
import constants
from exception import *

# global varibals
mail_thrs = {}
gui_thr = None
conf = None

lock = Lock()
messages = ({}, {})

JOIN_TIMEOUT = 1.0

class mail_thread(Thread):
    """This class creates the thread for fetching messages.

    @note: Public member variables:
        timer
    @note: Private member variables:
        __name
        __interval
        __mail_obj
    """

    def __init__(self, name, t, server, uname, password, ssl, h, interval,
                 mbox = 'INBOX'):
        """Override constructor

        @type name: string
        @param name: account name
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

        global mail_thrs

        Thread.__init__(self, None, None, 'mail-thread-%d' % len(mail_thrs),
                        (), {})
        self.setDaemon(True)

        self.__name = name
        self.__interval = float(interval)
        if not globals().has_key('%sprl' % t):
            print >> sys.stderr, _('pymailheaders: unknown server type')
            sys.exit(1)
        self.__mail_obj = getattr(globals()['%sprl' % t], t)(server,
                                                             uname,
                                                             password,
                                                             ssl,
                                                             h,
                                                             mbox)
        self.__connected = False
        self.timer = Event()

    def fetch(self):
        """Check and get mails

        This will set the global variables messages. messages will be in the form

        ({name: [(datetime, sender, subject), ...], ...},  <--- unread mails
         {name: [(datetime, sender, subject), ...], ...})  <--- read mails

        This allows each account to clear its own section when updating.
        """

        global messages
        global lock

        try:
            res = self.__mail_obj.get_mail()
            lock.acquire()
            messages[0][self.__name] = res[0]
            messages[1][self.__name] = res[1]
            lock.release()
        except Error, strerr:
            lock.acquire()
            messages[0].clear()
            messages[1].clear()
            messages[0][self.__name] = [(datetime.now(), _('Error'),
                                         str(strerr))]
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
            messages[0].clear()
            messages[1].clear()
            messages[0][self.__name] = [(datetime.now(), _('Error'),
                                         _('Network not available'))]
            lock.release()
        except Error, strerr:
            self.__connected = False
            lock.acquire()
            messages[0].clear()
            messages[1].clear()
            messages[0][self.__name] = [(datetime.now(), _('Error'),
                                         str(strerr))]
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
    """The variable passed to the GUI thread is in the following form

    ([(name, datetime, sender, subject), ...],  <--- unread mails
     [(name, datetime, sender, subject), ...])  <--- read mails

    sorted in reverse chronological order.
    """

    global lock
    global messages
    global gui_thr

    msgs = ([], [])

    lock.acquire()
    for k, v in messages[0].iteritems():
        for j in v:
            msgs[0].append((k, j[0], j[1], j[2]))
    for k, v in messages[1].iteritems():
        for j in v:
            msgs[1].append((k, j[0], j[1], j[2]))
    lock.release()

    cmp_func = lambda x, y: cmp(x[1], y[1])
    msgs[0].sort(cmp_func, reverse = True)
    msgs[1].sort(cmp_func, reverse = True)
    gui_thr.display(msgs)

def on_refresh_activate():
    global mail_thrs

    for acct in  mail_thrs.itervalues():
        gui.gobject.idle_add(acct.refresh)

def on_account_changed(opts):
    global conf
    global mail_thrs
    global lock
    global messages

    for k, v in opts.iteritems():
        delete_mail_thr(k)

        # if the account name has changed
        if 'name' in v:
            lock.acquire()
            if k in messages[0]:
                del messages[0][k]
            if k in messages[1]:
                del messages[1][k]
            lock.release()
            conf.remove_account(k)
            k = v['name']

        new_mail_thr(k, v)
        if k in mail_thrs and not mail_thrs[k].isAlive():
            mail_thrs[k].start()

def on_account_removed(name):
    global conf
    global lock
    global messages

    lock.acquire()
    if name in messages[0]:
        del messages[0][name]
    if name in messages[1]:
        del messages[1][name]
    lock.release()

    delete_mail_thr(name)
    conf.remove_account(name)

def on_config_save(opts):
    global conf

    if type(opts) != dict:
        return

    # write settings to config file
    for k, v in opts.iteritems():
        if k == 'accounts':
            for name, opt in v.iteritems():
                for i, j in opt.iteritems():
                    conf.set(i, j, name)
        else:
            conf.set(k, v)
    conf.write()

def on_exit(signum = None, frame = None):
    gui.gtk.quit()

def new_mail_thr(name, opts):
    global mail_thrs
    global gui_thr
    global conf

    if type(opts) != dict or name in mail_thrs:
        return

    acct = conf.make_empty_acct()
    acct.update(opts)

    if not acct['type'] or not acct['server'] or \
           (acct['auth'] and (not acct['username'] or not acct['password'])):
        gui_thr.show_settings(None)
        return

    h = gui_thr.get_max_messages()
    mail_thrs[name] = mail_thread(name, acct['type'], acct['server'],
                                  acct['username'], acct['password'],
                                  acct['encrypted'], h, acct['interval'])

def new_mail_thrs(opts):
    global mail_thrs
    global gui_thr

    if type(opts) != dict or mail_thrs:
        return

    for k, v in opts.iteritems():
        new_mail_thr(k, v)

def delete_mail_thr(name):
    global mail_thrs

    if not mail_thrs or name not in mail_thrs:
        return

    mail_thrs[name].timer.set()
    mail_thrs[name].join(JOIN_TIMEOUT)
    del mail_thrs[name]

def delete_mail_thrs():
    # get a list of all the mail threads first, otherwise the dictionary size
    # will change in the middle of this process
    keys = mail_thrs.keys()

    # stop all mail threads
    for k in keys:
        delete_mail_thr(k)

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
    global mail_thrs
    global messages

    # parse command-line arguments
    usage = 'usage: %prog [options]... args...'
    parser = OptionParser(usage)
    parser.add_option('-c', '--config-file', dest = 'config',
                      help = 'configuration file path')
    parser.add_option('-w', '--width', dest = 'width', type = 'int',
                      help = 'width of the window')
    parser.add_option('-g', '--height', dest = 'height', type = 'int',
                      help = 'height of the window')
    parser.add_option('--bg', dest = 'background', help = 'backgound color')
    parser.add_option('--fg', dest = 'foreground',
                      help = 'foreground color')
    parser.add_option('--fgn', dest = 'foreground new',
                      help = 'foreground color for new messages')
    parser.add_option('-l', '--log', dest = 'log',
                      help = 'Log file')
    parser.add_option('--level', dest = 'level',
                      help = 'Log level: critial, error, warning, info, debug')
    (options, args) = parser.parse_args()

    if options.config:
        exp_path = os.path.expanduser(options.config)
        config_file = os.path.isabs(exp_path) and exp_path or \
                      os.path.join(cwd, exp_path)
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

    # Logging information
    if 'log' in opts:
        TARGET = opts['log']
    else:
        TARGET = None
    LEVEL_LIST = {'critical': logging.CRITICAL,
                  'error': logging.ERROR,
                  'warning': logging.WARNING,
                  'info': logging.INFO,
                  'debug': logging.DEBUG}
    if 'level' in opts and opts['level'] in LEVEL_LIST:
        LEVEL = LEVEL_LIST[opts['level']]
    else:
        LEVEL = LEVEL_LIST['critical']
    FORMAT = '%(asctime)s [%(name)s:%(lineno)-4d] %(levelname)-5s: %(message)s'
    logging.basicConfig(level = LEVEL,
                        format = FORMAT,
                        datefmt = '%H:%M:%S',
                        filename = TARGET)

    # setup signal handler so that settings will be saved even if the
    # process is killed
    signal.signal(signal.SIGTERM, on_exit)

    # create threads
    gui_thr = gui.gui(opts)

    # set up signal handlers
    handlers = {'on_refresh_activate': on_refresh_activate,
                'on_config_save': on_config_save,
                'on_account_changed': on_account_changed,
                'on_account_removed': on_account_removed}
    gui_thr.signal_autoconnect(handlers)

    new_mail_thrs(opts['accounts'])

    try:
        # start all threads
        for mail_thr in mail_thrs.itervalues():
            if not mail_thr.isAlive():
                mail_thr.start()

        gui.gtk.gdk.threads_enter()
        gui.gtk.main()
        gui.gtk.gdk.threads_leave()
    except KeyboardInterrupt:
        pass

    delete_mail_thrs()

# rock n' roll
if __name__ == '__main__':
    main()
