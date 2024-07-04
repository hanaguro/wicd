#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   Copyright (C) 2021      Andreas Messer
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
#

import wicd.commandline
from wicd.utils import cached_property, singleton

@singleton
class log_manager(object):
    import logging as logging_

    default_format = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'

    class Logger(logging_.Logger):
        import logging

        def info(self, message):
            return self.log(level = self.logging.INFO, msg = message)

    logging_.setLoggerClass(Logger)

    @classmethod
    def LogLevel(cls, arg):
        try:
            level = int(arg)
        except ValueError:
            if arg.upper() not in cls.logging_._nameToLevel:
                raise wicd.commandline.ArgumentTypeError(f'{arg} is not a valid log level name')
        else:
            if level not in cls.logging_._levelToName:
                raise wicd.commandline.ArgumentTypeError(f'{level} is not a valid log level')
            arg = cls.logging_.getLevelName(level)

        return arg

    @cached_property
    def logging(self):
        level = wicd.commandline.get_args().loglevel
        self.logging_.basicConfig(format=self.default_format, level=level)
        return self.logging_

    def get_logger(self, name):
        return self.logging.getLogger(name)

wicd.commandline.get_parser().add_argument('--loglevel', type=log_manager.LogLevel,
                                        default='INFO', help='Enable logging messages with severity')


class LogAble(object):
    @cached_property
    def log(self):
        t = type(self)
        return log_manager.get_logger(f'{t.__module__}.{t.__name__}')



    