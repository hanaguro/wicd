#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   wicd development config file
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
""" wicd configuration file for development purposes. Eases debugging & local tests,
    distribution will receive autogenerated file """
import os.path
import os

# create a path within project folder to hold files for development purposes development files
devel_path = os.path.join(os.path.dirname(__file__), "..", "..", "devel_tmp")

if devel_path:
    etc_path = devel_path + "/etc/wicd"

    os.makedirs(etc_path, exist_ok = True)

    resolvconf_path        = devel_path + "/etc/resolv.conf"
    rundir_path            = devel_path + "/run/"

    if not os.path.exists(resolvconf_path):
        with open(resolvconf_path, "wt") as f:
            f.write("""\
            # Wicd Test resolv.conf
            search my.domain.home.arpa
            nameserver 127.0.0.1
            """)
else:
    etc_path        = "/etc/wicd"
    resolvconf_path = "/etc/resolv.conf"
    rundir_path     = "/var/run/wicd/"

wireless_conf_path = etc_path + os.sep + "wireless-settings.conf"
wired_conf_path    = etc_path + os.sep + "wired-settings.conf"
dhclient_conf_path = etc_path + os.sep + "dhclient.conf.template"

pidfile_path           = rundir_path + "wicd.pid"
resolvconf_backup_path = rundir_path + "resolv.conf.orig"