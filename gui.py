#!/usr/bin/env python
#
# gui.py
# Copyright 2008 Neil Shi <zeegeek@gmail.com>
#
# GTK+ GUI
# This file defines how the GUI looks like.
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

import sys
try:
    import pygtk
    pygtk.require('2.0')
    import gtk
    import gtk.glade
    import pango
    import gobject
except:
    print >> sys.stderr, 'PyGTK 2.6 or above has to be installed in ' + \
          'order to run Pymailheaders.'
    sys.exit(1)
import re

from constants import *
from exception import *

gtk.glade.bindtextdomain(NAME.lower(), 'po')
gtk.glade.textdomain(NAME.lower())

class gui(gtk.Window):
    """This class packs everything into the main window, and set up the
    alarm signal to check for new messages.

    @note: Private member variables:
        __tree
        __window
        __text
        __menu
        __buffer
        __new_tag
        __settings
        __acct_opts
        __disp_opts
        __set
        __opts
    """

    __acct_opts = {}
    __disp_opts = {}
    __set = {}
    __handlers = {'on_refresh_activate': None,
                  'on_config_save': None,
                  'on_account_changed': None}

    def __init__(self, opts):
        """
        @type opts: dict
        @param opts: a dictionary of all the settings
        """

        # have to start gtk thread before calling main()
        gobject.threads_init()
        gtk.gdk.threads_init()

        self.__opts = opts

        # read glade file
        glade_file = 'glade/pymailheaders.glade'
        self.__tree = gtk.glade.XML(glade_file)

        self.__window = self.__tree.get_widget('window')
        self.__menu = self.__tree.get_widget('menu')
        self.__settings = self.__tree.get_widget('settings')
        self.__text = self.__tree.get_widget('text')
        self.__buffer = self.__text.get_buffer()
        # text tag for new messages
        self.__new_tag = self.__buffer.create_tag()

        # create option name to function mapping
        self.__create_map()

        if not self.__window:
            raise Error('gui (__init__)',
                        _('Failed to get main window from glade file.'))
        self.__window.move(opts['x'], opts['y'])
        self.__window.set_title(NAME)

        self.__settings.set_transient_for(self)

        # apply saved settings
        for k, v in self.__set.iteritems():
            v(opts[k])

        # setting up signal handlers
        main_sigs = {'on_window_destroy': self.__close,
                     'on_window_configure_event': self.__position_changed,
                     'on_text_button_press_event': self.__button_press,
                     'on_text_expose_event': self.__on_redraw}
        menu_sigs = {'on_refresh_activate': self.__refresh,
                     'on_quit_activate': self.__close,
                     'on_about_activate': self.__show_about,
                     'on_settings_activate': self.show_settings}
        dial_sigs = {'on_type_changed': self.__type_changed,
                     'on_server_changed': self.__server_changed,
                     'on_auth_toggled': self.__auth_toggled,
                     'on_encrypted_toggled': self.__encrypted_toggled,
                     'on_username_changed': self.__username_changed,
                     'on_password_changed': self.__password_changed,
                     'on_interval_changed': self.__interval_changed,
                     # GUI settings
                     'on_size_changed': self.__size_changed,
                     'on_height_changed': self.__height_changed,
                     'on_width_changed': self.__width_changed,
                     'on_background_changed': self.__background_changed,
                     'on_foreground_changed': self.__foreground_changed,
                     'on_foreground_new_changed': self.__foreground_new_changed,
                     'on_font_changed': self.__font_changed,
                     'on_border_changed': self.__border_changed,
                     'on_decorated_toggled': self.__decorated_toggled,
                     'on_focus_toggled': self.__focus_toggled,
                     'on_top_toggled': self.__top_toggled,
                     'on_pager_toggled': self.__pager_toggled,
                     'on_taskbar_toggled': self.__taskbar_toggled,
                     'on_sticky_toggled': self.__sticky_toggled}
        self.__tree.signal_autoconnect(main_sigs)
        self.__tree.signal_autoconnect(menu_sigs)
        self.__tree.signal_autoconnect(dial_sigs)
        self.__settings.connect('response', self.__on_settings_response)

        self.__window.show()

    def __create_map(self):
        # Option name to function pointer mapping
        self.__set = {'height': lambda x: \
                      self.__resize_height(x),
                      'width': lambda x: \
                      self.__resize_width(x),
                      'background': lambda x: \
                      getattr(self.__text, 'modify_base')\
                      (gtk.STATE_NORMAL, gtk.gdk.color_parse(x)),
                      'foreground': lambda x: \
                      getattr(self.__text, 'modify_text')\
                      (gtk.STATE_NORMAL, gtk.gdk.color_parse(x)),
                      'foreground new': lambda x: \
                      getattr(self.__new_tag, 'set_property')\
                      ('foreground', x),
                      'font': lambda x: \
                      getattr(self.__text, 'modify_font')\
                      (pango.FontDescription(x)),
                      'border': lambda x: \
                      getattr(self.__window, 'set_border_width')\
                      (int(x)),
                      'decorated': getattr(self.__window, \
                                           'set_decorated'),
                      'focus': getattr(self.__window, \
                                       'set_accept_focus'),
                      'top': getattr(self.__window, \
                                     'set_keep_above'),
                      'pager': lambda x: \
                      getattr(self.__window, 'set_property')\
                      ('skip-pager-hint', not x),
                      'taskbar': lambda x: \
                      getattr(self.__window, 'set_property')\
                      ('skip-taskbar-hint', not x),
                      'sticky': lambda x: \
                      getattr(self.__window,
                              '%stick' % ((x and 's') or 'uns'))()}

    def __refresh(self, widget):
        if self.__handlers['on_refresh_activate']:
            self.__handlers['on_refresh_activate']()

    def __close(self, widget):
        self.__settings.destroy()
        gtk.main_quit()

    def __button_press(self, widget, event):
        # disable the signal first, so that it will not used to select
        # text.
        self.__text.emit_stop_by_name('button_press_event')

        if event.type == gtk.gdk.BUTTON_PRESS:
            if event.button == 1:
                # seems to be a bug of PyGTK here with
                # event.time argument, but it doesn't matter
                # that much
                self.__window.begin_move_drag(event.button, \
                                              int(event.x_root), \
                                              int(event.y_root), \
                                              event.time)
            elif event.button == 3:
                self.__menu.popup(None, None, None, \
                                  event.button, event.time)

    def __on_redraw(self, widget, event):
        text_window =  self.__text.get_window(gtk.TEXT_WINDOW_TEXT)
        text_window.set_cursor(gtk.gdk.Cursor(gtk.gdk.LEFT_PTR))

    def __position_changed(self, widget, event):
        # save position
        if event.x != self.__opts['x'] or event.y != self.__opts['y']:
            (self.__opts['x'], self.__opts['y']) = self.__window.get_position()
            self.__settings_save()

    def __show_about(self, widget):
        about = gtk.AboutDialog()
        about.set_transient_for(self)
        about.set_name(NAME)
        about.set_version(VERSION)
        about.set_comments(DESCRIPTION)
        about.set_copyright(COPYRIGHT)
        about.set_website_label('Homepage')
        about.set_website(HOMEPAGE)
        about.set_authors(AUTHOR)
        about.set_license(LICENSE)
        about.connect("response", lambda d, r: d.destroy())
        about.show()

    def __resize_height(self, h):
        self.__window.set_resizable(True)
        self.__text.set_property('height-request', h)
        self.__window.set_resizable(False)

    def __resize_width(self, w):
        self.__window.set_resizable(True)
        self.__text.set_property('width-request', w)
        self.__window.set_resizable(False)

    def __type_changed(self, widget):
        t = widget.get_active()

        if t == IMAP:
            self.__acct_opts['type'] = 'imap'
        elif t == POP:
            self.__acct_opts['type'] = 'pop'
        elif t == FEED:
            self.__acct_opts['type'] = 'feed'

    def __server_changed(self, widget):
        self.__acct_opts['server'] = widget.get_text()

    def __auth_toggled(self, widget):
        u = self.__tree.get_widget('username')
        p = self.__tree.get_widget('password')

        self.__acct_opts['auth'] = widget.get_active()

        if self.__acct_opts['auth']:
            u.set_sensitive(True)
            p.set_sensitive(True)
        else:
            u.set_sensitive(False)
            p.set_sensitive(False)
            u.set_text('')
            p.set_text('')

    def __encrypted_toggled(self, widget):
        self.__acct_opts['encrypted'] = widget.get_active()

    def __username_changed(self, widget):
        self.__acct_opts['username'] = widget.get_text()

    def __password_changed(self, widget):
        self.__acct_opts['password'] = widget.get_text()

    def __interval_changed(self, widget):
        self.__acct_opts['interval'] = int(widget.get_value())

    # GUI settings
    #
    # don't save the following settings into self.__opts until
    # __settings_save() is called.

    def __size_changed(self, widget):
        w = self.__tree.get_widget('width')
        h = self.__tree.get_widget('height')
        w_box = self.__tree.get_widget('width_hbox')
        h_box = self.__tree.get_widget('height_hbox')
        s = widget.get_active()

        if s == SIZE_CUSTOM:
            w_box.set_sensitive(True)
            h_box.set_sensitive(True)
            return
        else:
            w_box.set_sensitive(False)
            h_box.set_sensitive(False)

        if s == SIZE_SMALL:
            w.set_value(300)
            h.set_value(80)
        elif s == SIZE_MEDIUM:
            w.set_value(400)
            h.set_value(100)
        elif s == SIZE_BIG:
            w.set_value(600)
            h.set_value(130)

    def __height_changed(self, widget):
        self.__disp_opts['height'] = int(widget.get_value())
        self.__set['height'](self.__disp_opts['height'])

    def __width_changed(self, widget):
        self.__disp_opts['width'] = int(widget.get_value())
        self.__set['width'](self.__disp_opts['width'])

    def __background_changed(self, widget):
        c = widget.get_color()
        self.__disp_opts['background'] = '#%04x%04x%04x' % \
                                         (c.red, c.green, c.blue)
        self.__set['background'](self.__disp_opts['background'])

    def __foreground_changed(self, widget):
        c = widget.get_color()
        self.__disp_opts['foreground'] = '#%04x%04x%04x' % \
                                         (c.red, c.green, c.blue)
        self.__set['foreground'](self.__disp_opts['foreground'])

    def __foreground_new_changed(self, widget):
        c = widget.get_color()
        self.__disp_opts['foreground new'] = '#%04x%04x%04x' % \
                                             (c.red, c.green, c.blue)
        self.__set['foreground new'](self.__disp_opts['foreground new'])

    def __font_changed(self, widget):
        self.__disp_opts['font'] = widget.get_font_name()
        self.__set['font'](self.__disp_opts['font'])

    def __border_changed(self, widget):
        self.__disp_opts['border'] = int(widget.get_value())
        self.__set['border'](self.__disp_opts['border'])

    def __decorated_toggled(self, widget):
        self.__disp_opts['decorated'] = widget.get_active()
        self.__set['decorated'](self.__disp_opts['decorated'])

    def __focus_toggled(self, widget):
        self.__disp_opts['focus'] = widget.get_active()
        self.__set['focus'](self.__disp_opts['focus'])

    def __top_toggled(self, widget):
        self.__disp_opts['top'] = widget.get_active()
        self.__set['top'](self.__disp_opts['top'])

    def __pager_toggled(self, widget):
        self.__disp_opts['pager'] = widget.get_active()
        self.__set['pager'](self.__disp_opts['pager'])

    def __taskbar_toggled(self, widget):
        self.__disp_opts['taskbar'] = widget.get_active()
        self.__set['taskbar'](self.__disp_opts['taskbar'])

    def __sticky_toggled(self, widget):
        self.__disp_opts['sticky'] = widget.get_active()
        self.__set['sticky'](self.__disp_opts['sticky'])

    def __settings_cancel(self):
        self.__acct_opts.clear()
        for k in self.__disp_opts.iterkeys():
            self.__set[k](self.__opts[k])
        self.__disp_opts.clear()

    def __settings_save(self):
        acct_changed = False

        for k, v in self.__acct_opts.iteritems():
            if self.__opts[k] != self.__acct_opts[k]:
                acct_changed = True
                break

        # move all settings into self.__opts
        self.__opts.update(self.__acct_opts)
        self.__opts.update(self.__disp_opts)

        if acct_changed and self.__handlers['on_account_changed']:
            self.__handlers['on_account_changed'](self.__opts)

        # clean temporary settings
        self.__acct_opts.clear()
        self.__disp_opts.clear()

        if self.__handlers['on_config_save']:
            self.__handlers['on_config_save'](self.__opts)

    def __on_settings_response(self, dialog, response):
        if response == gtk.RESPONSE_OK:
            self.__settings_save()
        else:
            self.__settings_cancel()

        self.__settings.hide()

    def show_settings(self, widget):
        result = gtk.RESPONSE_CANCEL

        # initialize settings
        for k, v in self.__opts.iteritems():
            w = self.__tree.get_widget(k)
            t = type(v)
            if t == bool:
                # toggles
                w.set_active(v)
                continue
            elif t == int:
                # spinbuttons
                w and w.set_value(v)
                continue
            if k == 'type':
                v == 'imap' and w.set_active(IMAP)
                v == 'pop' and w.set_active(POP)
                v == 'feed' and w.set_active(FEED)
            elif k.find('ground') != -1:
                # color settings
                w.set_color(gtk.gdk.color_parse(v))
            elif k == 'font':
                not w.set_font_name(v) and \
                    gtk.MessageDialog(type = gtk.MESSAGE_ERROR, \
                                      message_format = \
                                      _('Font specified does not exist!'), \
                                      buttons = gtk.BUTTONS_OK)
            else:
                # normal strings
                w.set_text(v)
        self.__tree.get_widget('size').set_active(3)
        self.__settings.show()

    def signal_autoconnect(self, handlers):
        """Autoconnects signal handlers.

        @type handlers: dictionary
        @param handlers: dictionary of signal names and corresponding handlers.
        """

        if type(handlers) != dict:
            return

        for k, v in handlers.iteritems():
            if k in self.__handlers:
                self.__handlers[k] = v

    def get_font_size(self):
        """Get font size of text widget

        @rtype: int
        @return: font size
        """

        context =  self.__text.get_pango_context()
        size = context.get_font_description().get_size()
        return size / pango.SCALE

    def display(self, messages):
        """Display messages

        @type messages: list
        @param messages: list of tuples of flag, sender addresses and
            subjects, newest first.
        """

        def a(x):
            i = self.__buffer.get_end_iter()
            if x[0]:
                self.__buffer.insert_with_tags(i, \
                                               x[1] + ': ' + \
                                               x[2] + '\n',\
                                               self.__new_tag)
            else:
                self.__buffer.insert_with_tags(i, \
                                               x[1] + ': ' + \
                                               x[2] + '\n')

        # clear current view
        self.__buffer.delete(self.__buffer.get_start_iter(), \
                             self.__buffer.get_end_iter())
        # display messages
        map(a, messages)
