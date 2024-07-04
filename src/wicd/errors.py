#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   wicd exception definitions
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
import sys
import os

class WiCDError(Exception):
    pass


class WiCDDaemonNotFound(SystemExit, WiCDError):
    def __init__(self, val):
        super(WiCDDaemonNotFound, self).__init__(3)
        self.origin_exc = val

        sys.stderr.write(str(self)+ os.linesep)

    def __str__(self):
        return u"Failed to connect to wicd daemon: {}".format(self.origin_exc)
        

class transform_exception(object):
    def __init__(self, in_exc_type, out_exc_type):
        self.in_exc_type  = in_exc_type
        self.out_exc_type = out_exc_type

    def __call__(self, method):
        def transform_exception_wrapper(*args, **kwargs):
            try:
                return method(*args, **kwargs)
            except self.in_exc_type as e:
                raise self.out_exc_type(e)

        return transform_exception_wrapper