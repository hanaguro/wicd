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
import wicd.errors
import wicd.utils

import os.path
import subprocess

class ExternalCommand(object):

    def __init__(self, path_list):
        self.path_list = path_list

    @wicd.utils.cached_property
    def path(self):
        for p in self.path_list:
            if os.path.isfile(p):
                return p

        raise wicd.errors.WiCDCommandNotFound(f'Executable not found in {self.path_list}')

    def __call__(self, arg_or_list = [], *args):
        ''' executes external tool and returns ints output '''
        if isinstance(arg_or_list, str):
            arg_or_list = ( self.path, arg_or_list)  + args
        else:
            arg_or_list = ( self.path, ) + args

        # Run all commands in custom empty env, force english output for parsing
        env = {}
        env["LANG"] = env["LC_ALL"] = "C"
    
        try:
            p = subprocess.Popen(arg_or_list, shell=False, stdout=subprocess.PIPE, stdin=None, stderr=subprocess.PIPE,
                                 close_fds=True, env=env)
        except OSError as e:
            raise wicd.errors.WiCDPopenFailure(e)

        out, err = p.communicate()

        out = out.decode()
        err = err.decode()

        if p.returncode != 0:
            raise wicd.errors.WiCDCommandFailure(arg_or_list, p.returncode, out ,err)
        else:
            return out,err
