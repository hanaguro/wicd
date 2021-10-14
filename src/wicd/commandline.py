#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   wicd commandline handling
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

class CommandlineManager(object):
    ''' Central point to manage & access wicd command line arguments and their values '''
    import argparse

    parser = argparse.ArgumentParser(description = u'wire-d/-less connection daemon')

    @classmethod
    def get_parser(cls):
        return cls.parser

    @classmethod
    def get_args(cls):
        if hasattr(cls, "parser"):
            cls.args = cls.parser.parse_args()
            del cls.parser

        return cls.args

get_parser = CommandlineManager.get_parser

get_args   = CommandlineManager.get_args

del CommandlineManager

