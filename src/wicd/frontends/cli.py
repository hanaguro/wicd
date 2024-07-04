#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   Copyright (C) 2021       Andreas Messer
#
#   This program is free software; you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation; either version 2 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program; if not, write to the Free Software
#   Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#   MA 02110-1301, USA.

import wicd.commandline
import wicd.dbus

import sys
from wicd import misc
from wicd.translations import _

def main():
    parser = wicd.commandline.get_parser()
    parser.description = 'wicd command line interface'

    parser.add_argument('--network', '-n', type=int, default=-1)
    parser.add_argument('--network-property', '-p')
    parser.add_argument('--set-to', '-s')
    parser.add_argument('--name', '-m')

    parser.add_argument('--scan', '-S', default=False, action='store_true')
    parser.add_argument('--save', '-w', default=False, action='store_true')
    parser.add_argument('--list-networks', '-l', default=False, action='store_true')
    parser.add_argument('--network-details', '-d', default=False, action='store_true')
    parser.add_argument('--disconnect', '-x', default=False, action='store_true')
    parser.add_argument('--connect', '-c', default=False, action='store_true')
    parser.add_argument('--list-encryption-types', '-e', default=False, action='store_true')
    # short options for these aren't great.
    parser.add_argument('--wireless', '-y', default=False, action='store_true')
    parser.add_argument('--wired', '-z', default=False, action='store_true')
    parser.add_argument('--load-profile', '-o', default=False, action='store_true')
    parser.add_argument('--status', '-i', default=False,  action='store_true') # -i(nfo)

    args = wicd.commandline.get_args()

    daemon   = wicd.dbus.dbus_manager.ifaces['daemon']
    wireless = wicd.dbus.dbus_manager.ifaces['wireless']
    wired    = wicd.dbus.dbus_manager.ifaces['wired']
    config   = wicd.dbus.dbus_manager.ifaces['config']

    if not daemon:
        print(('Error connecting to wicd via D-Bus. ' + \
            'Please make sure the wicd service is running.'))
        sys.exit(3)


    exit_status = 0
    op_performed = False

    if not (args.wireless or args.wired or args.status):
        print(("Please use --wireless or --wired to specify " + \
        "the type of connection to operate on."))

    if args.status:
        status, info = daemon.GetConnectionStatus()
        if status in (misc.WIRED, misc.WIRELESS):
            connected = True
            status_msg = _('Connected')
            if status == misc.WIRED:
                conn_type = _('Wired')
            else:
                conn_type = _('Wireless')
        else:
            connected = False
            status_msg = misc._const_status_dict[status]

        print((_('Connection status') + ': ' + status_msg))
        if connected:
            print((_('Connection type') + ': ' + conn_type))
            if status == misc.WIRELESS:
                strength = daemon.FormatSignalForPrinting(info[2])
                print((_('Connected to $A at $B (IP: $C)') \
                    .replace('$A', info[1]) \
                    .replace('$B', strength) \
                    .replace('$C', info[0])))
                print((_('Network ID: $A') \
                    .replace('$A', info[3])))
            else:
                print((_('Connected to wired network (IP: $A)') \
                    .replace('$A', info[0])))
        else:
            if status == misc.CONNECTING:
                if info[0] == 'wired':
                    print((_('Connecting to wired network.')))
                elif info[0] == 'wireless':
                    print((_('Connecting to wireless network "$A".') \
                        .replace('$A', info[1])))
        op_performed = True

    # functions
    def is_valid_wireless_network_id(network_id):
        """ Check if it's a valid wireless network. '"""
        if not (network_id >= 0 \
                and network_id < wireless.GetNumberOfNetworks()):
            print('Invalid wireless network identifier.')
            sys.exit(1)

    def is_valid_wired_network_id(network_id):
        """ Check if it's a valid wired network. '"""
        num = len(wired.GetWiredProfileList())
        if not (network_id < num and \
                network_id >= 0):
            print('Invalid wired network identifier.')
            sys.exit(4)

    def is_valid_wired_network_profile(profile_name):
        """ Check if it's a valid wired network profile. '"""
        if not profile_name in wired.GetWiredProfileList():
            print('Profile of that name does not exist.')
            sys.exit(5)

    if args.scan and args.wireless:
        # synchronized scan
        wireless.Scan(True)
        op_performed = True

    if args.load_profile and args.wired:
        is_valid_wired_network_profile(args.name)
        wired.ReadWiredNetworkProfile(args.name)
        op_performed = True

    if args.list_networks:
        if args.wireless:
            print('#\tBSSID\t\t\tChannel\tESSID')
            for network_id in range(0, wireless.GetNumberOfNetworks()):
                print(('%s\t%s\t%s\t%s' % (network_id,
                    wireless.GetWirelessProperty(network_id, 'bssid'),
                    wireless.GetWirelessProperty(network_id, 'channel'),
                    wireless.GetWirelessProperty(network_id, 'essid'))))
        elif args.wired:
            print('#\tProfile name')
            i = 0
            for profile in wired.GetWiredProfileList():
                print(('%s\t%s' % (i, profile)))
                i += 1
        op_performed = True

    if args.network_details:
        if args.wireless:
            if args.network >= 0:
                is_valid_wireless_network_id(args.network)
                network_id = args.network
            else:
                network_id = wireless.GetCurrentNetworkID(0)
                is_valid_wireless_network_id(network_id)
                # we're connected to a network, print IP
                print(("IP: %s" % wireless.GetWirelessIP(0)))

            print(("Essid: %s" % wireless.GetWirelessProperty(network_id, "essid")))
            print(("Bssid: %s" % wireless.GetWirelessProperty(network_id, "bssid")))
            if wireless.GetWirelessProperty(network_id, "encryption"):
                print("Encryption: On")
                print(("Encryption Method: %s" % \
                    wireless.GetWirelessProperty(network_id, "encryption_method")))
            else:
                print("Encryption: Off")
            print(("Quality: %s" % \
                wireless.GetWirelessProperty(network_id, "quality")))
            print(("Mode: %s" % \
                wireless.GetWirelessProperty(network_id, "mode")))
            print(("Channel: %s" % \
                wireless.GetWirelessProperty(network_id, "channel")))
            print(("Bit Rates: %s" % \
                wireless.GetWirelessProperty(network_id, "bitrates")))
        op_performed = True

    # network properties

    if args.network_property:
        args.network_property = args.network_property.lower()
        if args.wireless:
            if args.network >= 0:
                is_valid_wireless_network_id(args.network)
                network_id = args.network
            else:
                network_id = wireless.GetCurrentNetworkID(0)
                is_valid_wireless_network_id(network_id)
            if not args.set_to:
                print((wireless.GetWirelessProperty(network_id,
                    args.network_property)))
            else:
                wireless.SetWirelessProperty(network_id, \
                        args.network_property, args.set_to)
        elif args.wired:
            if not args.set_to:
                print((wired.GetWiredProperty(args.network_property)))
            else:
                wired.SetWiredProperty(args.network_property, args.set_to)
        op_performed = True

    if args.disconnect:
        daemon.Disconnect()
        if args.wireless:
            if wireless.GetCurrentNetworkID(0) > -1:
                print(("Disconnecting from %s on %s" % \
                    (wireless.GetCurrentNetwork(0),
                    wireless.DetectWirelessInterface())))
        elif args.wired:
            if wired.CheckPluggedIn():
                print(("Disconnecting from wired connection on %s" % \
                    wired.DetectWiredInterface()))
        op_performed = True

    if args.connect:
        check = None
        if args.wireless and args.network > -1:
            is_valid_wireless_network_id(args.network)
            name = wireless.GetWirelessProperty(args.network, 'essid')
            encryption = wireless.GetWirelessProperty(args.network, 'enctype')
            print(("Connecting to %s with %s on %s" % (name, encryption,
                    wireless.DetectWirelessInterface())))
            wireless.ConnectWireless(args.network)

            check = wireless.CheckIfWirelessConnecting
            status = wireless.CheckWirelessConnectingStatus
            message = wireless.CheckWirelessConnectingMessage
        elif args.wired:
            print(("Connecting to wired connection on %s" % \
                wired.DetectWiredInterface()))
            wired.ConnectWired()

            check = wired.CheckIfWiredConnecting
            status = wired.CheckWiredConnectingStatus
            message = wired.CheckWiredConnectingMessage
        else:
            check = lambda: False
            status = lambda: False
            message = lambda: False

        # update user on what the daemon is doing
        last = None
        if check:
            while check():
                next_ = status()
                if next_ != last:
                    # avoid a race condition where status is updated to "done" after
                    # the loop check
                    if next_ == "done":
                        break
                    print((message()))
                    last = next_
            print("done!")
            if status() != 'done':
                exit_status = 6
            op_performed = True

    def str_properties(prop):
        """ Pretty print optional and required properties. """
        if len(prop) == 0:
            return "None"
        else:
            tmp = [(x[0], x[1].replace('_', ' ')) for x in type['required']]
            return ', '.join("%s (%s)" % (x, y) for x, y in tmp)

    if args.wireless and args.list_encryption_types:
        et = misc.LoadEncryptionMethods()
        # print 'Installed encryption templates:'
        print(('%s\t%-20s\t%s' % ('#', 'Name', 'Description')))
        i = 0
        for t in et:
            print(('%s\t%-20s\t%s' % (i, t['type'], t['name'])))
            print(('  Req: %s' % str_properties(t['required'])))
            print('---')
            # don't print optionals (yet)
            #print '  Opt: %s' % str_properties(type['optional'])
            i += 1
        op_performed = True

    if args.save and args.network > -1:
        if args.wireless:
            is_valid_wireless_network_id(args.network)
            config.SaveWirelessNetworkProfile(args.network)
        elif args.wired:
            config.SaveWiredNetworkProfile(args.name)
        op_performed = True

    if not op_performed:
        print("No operations performed.")

    sys.exit(exit_status)

if __name__ == '__main__':
    main()

