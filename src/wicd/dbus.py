#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   Copyright (C) 2008-2009 Adam Blackburn
#   Copyright (C) 2008-2009 Dan O'Reilly
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
import wicd.errors

import dbus.service as service
import dbus

wicd.commandline.get_parser().add_argument('--session-dbus', dest='DBus', 
    action='store_const', const=dbus.SessionBus, default=dbus.SystemBus,
    help=u"Use session instead of system dbus")

if getattr(dbus, "version", (0, 0, 0)) < (0, 80, 0):
    import dbus.glib
else:
    from dbus.mainloop.glib import DBusGMainLoop
    DBusGMainLoop(set_as_default=True)



class DBusManager(object):
    """ Manages the DBus objects used by wicd. """

    @property
    def bus(self):
        bus = self.__dict__['bus'] = wicd.commandline.get_args().DBus()
        return bus

    @property
    @wicd.errors.transform_exception(dbus.exceptions.DBusException, wicd.errors.WiCDDaemonNotFound)
    def daemon_iface(self):
        proxy_obj = self.bus.get_object("org.wicd.daemon", '/org/wicd/daemon')
        return dbus.Interface(proxy_obj, 'org.wicd.daemon')

    @property
    @wicd.errors.transform_exception(dbus.exceptions.DBusException, wicd.errors.WiCDDaemonNotFound)
    def wireless_iface(self):
        proxy_obj = self.bus.get_object("org.wicd.daemon", '/org/wicd/daemon/wireless')
        return dbus.Interface(proxy_obj, 'org.wicd.daemon.wireless')

    @property
    @wicd.errors.transform_exception(dbus.exceptions.DBusException, wicd.errors.WiCDDaemonNotFound)
    def wired_iface(self):
        proxy_obj = self.bus.get_object("org.wicd.daemon", '/org/wicd/daemon/wired')
        return dbus.Interface(proxy_obj, 'org.wicd.daemon.wired')

    @property
    @wicd.errors.transform_exception(dbus.exceptions.DBusException, wicd.errors.WiCDDaemonNotFound)
    def config_iface(self):
        proxy_obj = self.bus.get_object("org.wicd.daemon", '/org/wicd/daemon/config')
        return dbus.Interface(proxy_obj, 'org.wicd.daemon')


    @property
    def ifaces(self):
        ifaces = self.__dict__['ifaces'] = {
            "daemon" : self.daemon_iface, 
            "wireless" : self.wireless_iface,
            "wired" :    self.wired_iface,
            "config" :   self.config_iface,
        }

        return ifaces
    
    def get_dbus_ifaces(self):
        """ Returns a dict of dbus interfaces. """
        return self.ifaces
    
    def get_interface(self, iface):
        """ Returns a DBus Interface. """
        return self.ifaces[iface]
    
    def get_bus(self):
        """ Returns the loaded SystemBus. """
        return self.bus
    
    def set_mainloop(self, loop):
        """ Set DBus main loop. """
        dbus.set_default_main_loop(loop)
    
    def connect(self):
        self.ifaces

dbus_manager = DBusManager()
del DBusManager
        
method = service.method