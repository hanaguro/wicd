#!/usr/bin/env python3
#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
#   Copyright (C) 2009        Andrew Psaltis
#   Copyright (C) 2021        Andreas Messer
#
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
from setuptools import setup, find_packages
from distutils.command.build_py import build_py as _build_py

data = []

py_modules = ['wicd.networking','wicd.misc','wicd.wnettools',
              'wicd.wpath','wicd.dbusmanager',
              'wicd.logfile','wicd.backend','wicd.configmanager',
              'wicd.translations']

class CustomPyBuild(_build_py):
    def run(self):
        super().run()

setup(
    description = "A wireless and wired network manager",
    long_description = """A complete network connection manager
Wicd supports wired and wireless networks, and capable of
creating and tracking profiles for both.  It has a 
template-based wireless encryption system, which allows the user
to easily add encryption methods used.  It ships with some common
encryption types, such as WPA and WEP. Wicd will automatically
connect at startup to any preferred network within range.
""",

    author = "Tom Van Braeckel, Adam Blackburn, Dan O'Reilly, Andrew Psaltis, David Paleino, Andreas Messer",
    author_email = "tomvanbraeckel@gmail.com, compwiz18@gmail.com, oreilldf@gmail.com, ampsaltis@gmail.com, d.paleino@gmail.com, andi@bastelmap.de",
    url = "https://launchpad.net/wicd",
    license = "http://www.gnu.org/licenses/old-licenses/gpl-2.0.html",

    packages    = find_packages("src"),
    cmdclass    = { "build_py" : CustomPyBuild },
)
