#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   Copyright (C) 2007 - 2009 Adam Blackburn
#   Copyright (C) 2007 - 2009 Dan O'Reilly
#   Copyright (C) 2009        Andrew Psaltis
#   Copyright (C) 2021 - 2022 Andreas Messer
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
from setuptools.command.build_py import build_py
import os

config_file_template = '''
import os

etc_path        = "/etc/wicd"
resolvconf_path = "/etc/resolv.conf"
rundir_path     = "/var/run/wicd/"

wireless_conf_path = etc_path + os.sep + "wireless-settings.conf"
wired_conf_path    = etc_path + os.sep + "wired-settings.conf"
dhclient_conf_path = etc_path + os.sep + "dhclient.conf.template"

pidfile_path           = rundir_path + "wicd.pid"
resolvconf_backup_path = rundir_path + "resolv.conf.orig"
'''

class wicd_build_py(build_py):
    def run(self):
        config_file = os.path.join(self.build_lib, 'wicd', 'config.py')

        with open(config_file, 'wt') as f:
            print('generating ' + config_file)
            f.write(config_file_template);

        super().run()

def version_scheme(version):
    if version.exact:
        return version.format_with("{tag}")
    else:
        return "git"

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
    setup_requires = ['setuptools_scm'],
    use_scm_version = {
        "version_scheme" : version_scheme,
    },

    author = "Tom Van Braeckel, Adam Blackburn, Dan O'Reilly, Andrew Psaltis, David Paleino, Andreas Messer",
    author_email = "tomvanbraeckel@gmail.com, compwiz18@gmail.com, oreilldf@gmail.com, ampsaltis@gmail.com, d.paleino@gmail.com, andi@bastelmap.de",
    url = "https://launchpad.net/wicd",
    license = "http://www.gnu.org/licenses/old-licenses/gpl-2.0.html",

    cmdclass    = { "build_py" : wicd_build_py },
)
