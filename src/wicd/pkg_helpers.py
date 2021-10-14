
#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   wicd package access helper
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
import pkg_resources  # part of setuptools
import importlib.resources
import os.path

def get_dist():
    for d in pkg_resources.require("wicd"):
        if os.path.commonprefix([d.module_path, __file__]) == d.module_path:
            return d
    
    raise ValueError(u'Unable to retrieve current distribution')
    
def get_version():
    return get_dist().version

def read_resource_file(path):
    return importlib.resources.read_binary("wicd", path)