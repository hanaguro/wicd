#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   wicd dns resolver manager
#
#   Copyright (C) 2021 Andreas Messer
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License Version 2 as
#   published by the Free Software Foundation.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

class cached_property(object):
    def __init__(self, fget):
        self.fget = fget

    def __get__(self, obj, objtype = None):
        retval = obj.__dict__[self.fget.__name__] = self.fget.__get__(obj, objtype)()
        return retval

