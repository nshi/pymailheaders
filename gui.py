#!/usr/bin/env python
#
# gui.py
# Copyright 2007 Neil Shi <zeegeek@gmail.com>
#
# GUI using TkInter
# This file defines how the UI looks like.
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

from Tkinter import *
import re

import constants

class gui(Tk):
	"""This class packs everything into the main window, and set up the
	alarm signal to check for new messages.

	@note: Private member variables:
		__text
	"""

	def __init__(self, geometry, fg, bg, fg_new):
		"""
		@type geometry: string
		@param geometry: geometry string in the form 'wxh+x+y'
		@type fg: string
		@param fg: foreground color, there are two forms to specify
			colors: '#fff' or 'white'.
		@type bg: string
		@param bg: same as I{fg}, but for background color.
		@type fg_new: string
		@param fg_new: foreground color for new messages.
		"""

		Tk.__init__(self)
		self.geometry(geometry)
		self.resizable(False, False)
		self.title(constants.NAME)
		
		# define layout
		self.__text = Text(self, \
				   bg = bg, \
				   fg = fg, \
				   cursor = 'pirate', \
				   state = DISABLED, \
				   relief = GROOVE, \
				   wrap = NONE)
		self.__text.tag_config('new', foreground = fg_new)
		self.__text.grid(sticky = N + E + S + W)

	def get_font_size(self):
		"""Get font size of text widget

		@rtype: int
		@return: font size
		"""

		return int(re.search('(\d+)', self.__text['font']).group(1))

	def display(self, messages):
		"""Display messages

		@type messages: list
		@param messages: list of tuples of flag, sender addresses and
			subjects, newest first.
		"""

		def a(x):
			if x[0]:
				self.__text.insert(END, \
						   x[1] + ': ' + x[2] + '\n', \
						   'new')
			else:
				self.__text.insert(END, \
						   x[1] + ': ' + x[2] + '\n')
					   
		# enable widget
		self.__text['state'] = NORMAL

		# clear current view
		self.__text.delete(1.0, END)
		# display messages
		map(a, messages)
		# redraw widget
		self.__text.update_idletasks()

		# disable widget
		self.__text['state'] = DISABLED
