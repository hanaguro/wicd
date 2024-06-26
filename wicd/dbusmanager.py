#!/usr/bin/env python3

""" The wicd DBus Manager.

A module for managing wicd's dbus interfaces.

"""

#
#   Copyright (C) 2008-2009 Adam Blackburn
#   Copyright (C) 2008-2009 Dan O'Reilly
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

import dbus
from dbus.mainloop.glib import DBusGMainLoop

DBusGMainLoop(set_as_default=True)

DBUS_MANAGER = None

def get_dbus_ifaces():
    """ Return available DBus interfaces. """
    return DBUS_MANAGER.get_dbus_ifaces()

def get_interface(iface):
    """ Return specified interface. """
    return DBUS_MANAGER.get_interface(iface)

def get_bus():
    """ Return the loaded System Bus. """
    return DBUS_MANAGER.get_bus()

def set_mainloop(loop):
    """ Set DBus main loop. """
    return DBUS_MANAGER.set_mainloop(loop)

def connect_to_dbus():
    """ Connect to DBus. """
    return DBUS_MANAGER.connect_to_dbus()

def threads_init():
    """ Init GLib threads. """
    from gi.repository import GLib
    GLib.threads_init()


class DBusManager(object):
    """ Manages the DBus objects used by wicd. """
    def __init__(self):
        self._bus = dbus.SystemBus()
        self._dbus_ifaces = {}

    def get_dbus_ifaces(self):
        """ Returns a dict of dbus interfaces. """
        if not self._dbus_ifaces:
            connect_to_dbus()
        return self._dbus_ifaces

    def get_interface(self, iface):
        """ Returns a DBus Interface. """
        if not self._dbus_ifaces:
            connect_to_dbus()
        return self._dbus_ifaces[iface]

    def get_bus(self):
        """ Returns the loaded SystemBus. """
        return self._bus

    def set_mainloop(self, loop):
        """ Set DBus main loop. """
        dbus.set_default_main_loop(loop)

    def connect_to_dbus(self):
        """ Connects to wicd's dbus interfaces and loads them into a dict. """
        proxy_obj = self._bus.get_object("org.wicd.daemon", '/org/wicd/daemon')
        daemon = dbus.Interface(proxy_obj, 'org.wicd.daemon')

        proxy_obj = self._bus.get_object("org.wicd.daemon",
                                         '/org/wicd/daemon/wireless')
        wireless = dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')

        proxy_obj = self._bus.get_object("org.wicd.daemon",
                                         '/org/wicd/daemon/wired')
        wired = dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')

        self._dbus_ifaces = {"daemon" : daemon, "wireless" : wireless,
                             "wired" : wired}

DBUS_MANAGER = DBusManager()
