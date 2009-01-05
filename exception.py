#!/usr/bin/env python
#
# exception.py
# Copyright 2008 Neil Shi <zeegeek@gmail.com>
#
# Exception definitions
# This file defines all the exceptions used by pymailheaders
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

from sys import stderr

class Error(Exception):
    """Normal error.

    @note: Public member variables:
        where
        what
    """

    def __init__(self, where, what):
        self.where = where
        self.what = what and what or ''

    def __str__(self):
        return ': '.join([self.where, self.what])

class TryAgain(Error):
    """Network temporarily unavailable, try again."""
    pass
