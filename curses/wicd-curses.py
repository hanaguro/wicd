# -*- coding: utf-8 -*-

CURSES_REV = "1.0.0"  # 適切なバージョン番号を設定

""" wicd-curses. (curses/urwid-based) console interface to wicd

Provides a console UI for wicd, so that people with broken X servers can
at least get a network connection.  Or those who don't like using X and/or GTK.

"""

#       Copyright (C) 2008-2009 Andrew Psaltis

#       This program is free software; you can redistribute it and/or modify
#       it under the terms of the GNU General Public License as published by
#       the Free Software Foundation; either version 2 of the License, or
#       (at your option) any later version.
#
#       This program is distributed in the hope that it will be useful,
#       but WITHOUT ANY WARRANTY; without even the implied warranty of
#       MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#       GNU General Public License for more details.
#
#       You should have received a copy of the GNU General Public License
#       along with this program; if not, write to the Free Software
#       Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#       MA 02110-1301, USA.


# This contains/will contain A LOT of code from the other parts of wicd.
#
# This is probably due to the fact that I did not really know what I was doing
# when I started writing this.  It works, so I guess that's all that matters.
#
# Comments, criticisms, patches, bug reports all welcome!

# Filter out a confusing urwid warning in python 2.6.
# This is valid as of urwid version 0.9.8.4
import warnings
warnings.filterwarnings(
    "ignore",
    "The popen2 module is deprecated.  Use the subprocess module."
)
import urwid
# DBus communication stuff
from dbus import DBusException
from gi.repository import GLib as gobject


# Other important wicd-related stuff
from wicd import wpath
from wicd import misc
from wicd import dbusmanager

# Internal Python stuff
import sys

# SIGQUIT signal handling
import signal

# Curses UIs for other stuff
from curses_misc import ComboBox, Dialog2, NSelListBox, SelText, OptCols
from curses_misc import TextDialog, InputDialog, error, DynEdit, DynIntEdit
from prefs_curses import PrefsDialog

import netentry_curses
from netentry_curses import WirelessSettingsDialog, WiredSettingsDialog

from optparse import OptionParser
from wicd.translations import _

ui = None
loop = None
bus = daemon = wireless = wired = None

########################################
##### SUPPORT CLASSES
########################################
# Yay for decorators!
def wrap_exceptions(func):
    """ Decorator to wrap exceptions. """
    def wrapper(*args, **kargs):
        try:
            return func(*args, **kargs)
        except KeyboardInterrupt:
            loop.quit()
            ui.stop()
            print("\n" + _('Terminated by user'), file=sys.stderr)
        except DBusException:
            loop.quit()
            ui.stop()
            print("\n" + _('DBus failure! '
                'This is most likely caused by the wicd daemon '
                'stopping while wicd-curses is running. '
                'Please restart the daemon, and then restart wicd-curses.'), file=sys.stderr)
            raise
        except:
            # Quit the loop
            #if 'loop' in locals():
            loop.quit()
            # Zap the screen
            ui.stop()
            # Print out standard notification:
            # This message was far too scary for humans, so it's gone now.
            # print >> sys.stderr, "\n" + _('EXCEPTION! Please report this '
            # 'to the maintainer and file a bug report with the backtrace '
            # 'below:')
            # Flush the buffer so that the notification is always above the
            # backtrace
            sys.stdout.flush()
            # Raise the exception
            raise

    wrapper.__name__ = func.__name__
    wrapper.__module__ = func.__module__
    wrapper.__dict__ = func.__dict__
    wrapper.__doc__ = func.__doc__
    return wrapper

class WiredComboBox(ComboBox):
    def __init__(self, l):
        self.ADD_PROFILE = '---' + _('Add a new profile') + '---'
        super().__init__(use_enter=False)
        self.theList = []
        self.set_list(l)

    def get_selected_profile(self):
        # theListの現在の選択を返す
        return self.theList[self.get_focus()[1]] if self.theList and len(self.theList) > 0 else None


class NetLabel(urwid.WidgetWrap):
    """ Wireless network label. """
    def __init__(self, i, is_active):
        # Pick which strength measure to use based on what the daemon says
        # gap allocates more space to the first module
        if daemon.GetSignalDisplayType() == 0:
            strenstr = 'quality'
            gap = 4  # Allow for 100%
        else:
            strenstr = 'strength'
            gap = 7  # -XX dbm = 7
        self.id = i
        # All of that network property stuff
        self.stren = daemon.FormatSignalForPrinting(
                str(wireless.GetWirelessProperty(self.id, strenstr)))
        self.essid = wireless.GetWirelessProperty(self.id, 'essid')
        self.bssid = wireless.GetWirelessProperty(self.id, 'bssid')

        if wireless.GetWirelessProperty(self.id, 'encryption'):
            self.encrypt = wireless.GetWirelessProperty(self.id, 'encryption_method')
        else:
            self.encrypt = _('Unsecured')
        self.mode = wireless.GetWirelessProperty(self.id, 'mode')
        self.channel = wireless.GetWirelessProperty(self.id, 'channel')
        theString = '  %-*s %25s %9s %17s %6s %4s' % (
            gap, self.stren, self.essid, self.encrypt, self.bssid, self.mode,
            self.channel)
        if is_active:
            theString = '>' + theString[1:]
            w = urwid.AttrMap(SelText(theString), 'connected', 'connected focus')
        else:
            w = urwid.AttrMap(SelText(theString), 'body', 'focus')
        super().__init__(w)

    def selectable(self):
        """ Return whether the widget is selectable. """
        return True

    def keypress(self, size, key):
        """ Handle keypresses. """
        return self._w.keypress(size, key)

    def connect(self):
        """ Execute connection. """
        wireless.ConnectWireless(self.id)

class appGUI():
    """The UI itself, all glory belongs to it!"""
    def __init__(self):
        self.conn_status = False
        self.tcount = 0  # Counter for connection twirl indicator
        self.size = ui.get_cols_rows()
        self.screen_locker = urwid.Filler(urwid.Text(('important', _('Scanning networks... stand by...')), align='center'))
        self.no_wlan = urwid.Filler(urwid.Text(('important', _('No wireless networks found.')), align='center'))
        self.TITLE = _('Wicd Curses Interface')
        self.WIRED_IDX = 1
        self.WLESS_IDX = 3
        header = urwid.AttrMap(urwid.Text(self.TITLE, align='right'), 'header')
        self.wiredH = urwid.Filler(urwid.Text(_('Wired Networks')))
        self.list_header = urwid.AttrMap(urwid.Text(gen_list_header()), 'listbar')
        self.wlessH = NSelListBox([urwid.Text(_('Wireless Networks')), self.list_header])
        self.update_tag = None
        self.focusloc = [1, 0]
        wiredL, wlessL = [], []
        self.frame = None
        self.diag = None
        self.wiredCB = urwid.Filler(WiredComboBox(wiredL))
        self.wlessLB = urwid.ListBox(wlessL)
        self.update_netlist(force_check=True, firstrun=True)
        keys = [
            ('H', _('Help'), None),
            ('right', _('Config'), None),
            ('K', _('RfKill'), None),
            ('C', _('Connect'), None),
            ('D', _('Disconn'), None),
            ('R', _('Refresh'), None),
            ('P', _('Prefs'), None),
            ('I', _('Hidden'), None),
            ('A', _('About'), None),
            ('Q', _('Quit'), loop.quit)
        ]
        self.primaryCols = OptCols(keys, self.handle_keys)
        self.status_label = urwid.AttrMap(urwid.Text(''), 'important')
        self.footer2 = urwid.Columns([self.status_label])
        self.footerList = urwid.Pile([self.primaryCols, self.footer2])
        self.frame = urwid.Frame(self.thePile, header=header, footer=self.footerList)
        self.wiredCB.original_widget.build_combobox(self.frame, ui, 3)
        self.init_other_optcols()
        self.frame.set_body(self.thePile)
        self.prev_state = False
        self.connecting = False
        self.screen_locked = False
        self.do_diag_lock = False
        self.diag_type = 'none'
        self.scanning = False
        self.pref = None
        self.update_status()



    def doScan(self, sync=False):
        """ Start wireless scan. """
        self.scanning = True
        wireless.Scan(False)

    def init_other_optcols(self):
        """ Init "tabbed" preferences dialog. """
        self.prefCols = OptCols([
            ('S', _('Save')),
            ('page up', _('Tab Left'), ),
            ('page down', _('Tab Right')),
            ('esc', _('Cancel'))
        ], self.handle_keys)
        self.confCols = OptCols([
            ('S', _('Save')),
            ('Q', _('Cancel'))
        ], self.handle_keys)

    def lock_screen(self):
        """ Lock the screen. """
        if self.diag_type == 'pref':
            self.do_diag_lock = True
            return True
        self.frame.set_body(self.screen_locker)
        self.screen_locked = True
        self.update_ui()

    def unlock_screen(self):
        """ Unlock the screen. """
        if self.do_diag_lock:
            self.do_diag_lock = False
            return True
        self.update_netlist(force_check=True)
        if not self.diag:
            self.frame.set_body(self.thePile)
        self.screen_locked = False
        self.update_ui()

    def raise_hidden_network_dialog(self):
        """ Show hidden network dialog. """
        dialog = InputDialog(
            ('header', _('Select Hidden Network ESSID')),
            7, 30, _('Scan')
        )
        exitcode, hidden = dialog.run(ui, self.frame)
        if exitcode != -1:
            # That dialog will sit there for a while if I don't get rid of it
            self.update_ui()
            wireless.SetHiddenNetworkESSID(misc.noneToString(hidden))
            wireless.Scan(False)
        wireless.SetHiddenNetworkESSID("")

    def update_focusloc(self):
        if self.thePile.get_focus() == self.wiredCB:
            wlessorwired = self.WIRED_IDX
            where = self.thePile.get_focus().original_widget.get_focus()[1]
        else:
            wlessorwired = self.WLESS_IDX
            if self.wlessLB == self.no_wlan:
                where = None
            else:
                where = self.thePile.get_focus().get_focus()[1]
        self.focusloc = [wlessorwired, where]

    # Be clunky until I get to a later stage of development.
    # Update the list of networks.  Usually called by DBus.
    @wrap_exceptions
    def update_netlist(self, state=None, x=None, force_check=False, firstrun=False):
        """ Update the list of networks. """
        # Don't even try to do this if we are running a dialog
        if self.diag:
            return
        # Run focus-collecting code if we are not running this for the first
        # time
        if not firstrun:
            self.update_focusloc()
            self.list_header.original_widget.set_text(gen_list_header())
        # Updates the overall network list.
        if not state:
            state, trash = daemon.GetConnectionStatus()
        if force_check or self.prev_state != state:
            wiredL, wlessL = gen_network_list()
            self.wiredCB.original_widget.set_list(wiredL)
            self.wiredCB.original_widget.build_combobox(self.frame, ui, 3)
            if len(wlessL) != 0:
                if self.wlessLB == self.no_wlan:
                    self.wlessLB = urwid.ListBox(wlessL)
                else:
                    self.wlessLB.body = urwid.SimpleListWalker(wlessL)
            else:
                self.wlessLB = self.no_wlan
            if daemon.GetAlwaysShowWiredInterface() or wired.CheckPluggedIn():
                self.thePile = urwid.Pile([
                    ('fixed', 1, self.wiredH),
                    ('fixed', 1, self.wiredCB),
                    ('fixed', 2, self.wlessH),
                    self.wlessLB]
                )
                if not firstrun:
                    self.frame.body = self.thePile

                self.thePile.set_focus(self.focusloc[0])
                if self.focusloc[0] == self.WIRED_IDX:
                    self.thePile.get_focus().original_widget.set_focus(self.focusloc[1])
                else:
                    if self.wlessLB != self.no_wlan:
                        # Set the focus to the last selected item, but never past the length of the list
                        self.thePile.get_focus().set_focus(min(self.focusloc[1], len(wlessL) - 1))
                    else:
                        self.thePile.set_focus(self.wiredCB)
            else:
                self.thePile = urwid.Pile([
                    ('fixed', 2, self.wlessH),
                    self.wlessLB
                ])
                if not firstrun:
                    self.frame.body = self.thePile
                if self.focusloc[1] is None:
                    self.focusloc[1] = 0
                if self.wlessLB != self.no_wlan:
                    # Set the focus to the last selected item, but never past the length of the list
                    self.wlessLB.set_focus(min(self.focusloc[1], len(wlessL) - 1))

        self.prev_state = state
        if not firstrun:
            self.update_ui()
        if firstrun:
            if wired.GetDefaultWiredNetwork() is not None:
                self.wiredCB.original_widget.set_focus(wired.GetWiredProfileList().index(wired.GetDefaultWiredNetwork()))


    @wrap_exceptions
    def update_status(self):
        """ Update the footer / statusbar. """
        wired_connecting = wired.CheckIfWiredConnecting()
        wireless_connecting = wireless.CheckIfWirelessConnecting()
        self.connecting = wired_connecting or wireless_connecting

        fast = not daemon.NeedsExternalCalls()
        if self.connecting:
            if not self.conn_status:
                self.conn_status = True
                gobject.timeout_add(250, self.set_connecting_status, fast)
            return True
        else:
            if check_for_wired(wired.GetWiredIP(''), self.set_status):
                return True
            if not fast:
                iwconfig = wireless.GetIwconfig()
            else:
                iwconfig = ''
            if check_for_wireless(iwconfig, wireless.GetWirelessIP(""), self.set_status):
                return True
            else:
                self.set_status(_('Not connected'))
                self.update_ui()
                return True

    def set_connecting_status(self, fast):
        """ Set connecting status. """
        wired_connecting = wired.CheckIfWiredConnecting()
        wireless_connecting = wireless.CheckIfWirelessConnecting()
        if wireless_connecting:
            if not fast:
                iwconfig = wireless.GetIwconfig()
            else:
                iwconfig = ''
            essid = wireless.GetCurrentNetwork(iwconfig)
            stat = wireless.CheckWirelessConnectingMessage()
            return self.set_status("%s: %s" % (essid, stat), True)
        if wired_connecting:
            return self.set_status(_('Wired Network') + ': ' + wired.CheckWiredConnectingMessage(), True)
        else:
            self.conn_status = False
            return False


    def set_status(self, text, from_idle=False):
        """ Set the status text. """
        # Set the status text, usually called by the update_status method
        # from_idle : a check to see if we are being called directly from the
        # mainloop
        # If we are being called as the result of trying to connect to
        # something, and we aren't connecting to something, return False
        # immediately.

        # Cheap little indicator stating that we are actually connecting
        twirl = ['|', '/', '-', '\\']

        if from_idle and not self.connecting:
            self.update_status()
            self.conn_status = False
            return False
        toAppend = ''
        # If we are connecting and being called from the idle function, spin
        # the wheel.
        if from_idle and self.connecting:
            # This is probably the wrong way to do this, but it works for now.
            self.tcount += 1
            toAppend = twirl[self.tcount % 4]
        self.status_label.original_widget.set_text(text + ' ' + toAppend)
        self.update_ui()
        return True

    def dbus_scan_finished(self):
        """ Handle DBus scan finish. """
        # I'm pretty sure that I'll need this later.
        #if not self.connecting:
        #    gobject.idle_add(self.refresh_networks, None, False, None)
        self.unlock_screen()
        self.scanning = False

    def dbus_scan_started(self):
        """ Handle DBus scan start. """
        self.scanning = True
        if self.diag_type == 'conf':
            self.restore_primary()
        self.lock_screen()

    def restore_primary(self):
        """ Restore screen. """
        self.diag_type = 'none'
        if self.do_diag_lock or self.scanning:
            self.frame.set_body(self.screen_locker)
            self.do_diag_lock = False
        else:
            self.frame.set_body(self.thePile)
        self.diag = None
        self.frame.set_footer(urwid.Pile([self.primaryCols, self.footer2]))
        self.update_ui()

    def handle_keys(self, keys):
        """ Handle keys. """
        if not self.diag:
            # Handle keystrokes
            if "f8" in keys or 'Q' in keys or 'q' in keys:
                loop.quit()
            if "f5" in keys or 'R' in keys:
                self.lock_screen()
                self.doScan()
            if 'k' in keys or 'K' in keys:
                wireless.SwitchRfKill()
                self.update_netlist()
            if "D" in keys:
                daemon.Disconnect()
                self.update_netlist()
            if 'right' in keys:
                if not self.scanning:
                    focus = self.thePile.get_focus()
                    self.frame.set_footer(
                        urwid.Pile([self.confCols, self.footer2])
                    )
                    if focus == self.wiredCB:
                        self.diag = WiredSettingsDialog(
                            self.wiredCB.original_widget.get_selected_profile(),
                            self.frame
                        )
                        self.diag.ready_widgets(ui, self.frame)
                        self.frame.set_body(self.diag)
                    else:
                        # wireless list only other option
                        trash, pos = self.thePile.get_focus().get_focus()
                        self.diag = WirelessSettingsDialog(pos, self.frame, ui)
                        self.diag.ready_widgets(ui, self.frame)
                        self.frame.set_body(self.diag)
                    self.diag_type = 'conf'
            if "enter" in keys or 'C' in keys:
                if not self.scanning:
                    focus = self.frame.body.get_focus()
                    if focus == self.wiredCB:
                        self.special = focus
                        self.connect("wired", 0)
                    else:
                        # wless list only other option, if it is around
                        if self.wlessLB != self.no_wlan:
                            wid, pos = self.thePile.get_focus().get_focus()
                            self.connect("wireless", pos)
            if "esc" in keys:
                # Force disconnect here if connection in progress
                if self.connecting:
                    daemon.CancelConnect()
                    # Prevents automatic reconnecting if that option is enabled
                    daemon.SetForcedDisconnect(True)
            if "P" in keys:
                if not self.pref:
                    self.pref = PrefsDialog(
                        self.frame,
                        (0, 1),
                        ui,
                        dbusmanager.get_dbus_ifaces()
                    )
                self.pref.load_settings()
                self.pref.ready_widgets(ui, self.frame)
                self.frame.set_footer(urwid.Pile([self.prefCols, self.footer2]))
                self.diag = self.pref
                self.diag_type = 'pref'
                self.frame.set_body(self.diag)
                # Halt here, keypress gets passed to the dialog otherwise
                return True
            if "A" in keys:
                about_dialog(self.frame)
            if "I" in keys:
                self.raise_hidden_network_dialog()
            if "H" in keys or 'h' in keys or '?' in keys:
                # FIXME I shouldn't need this, OptCols messes up this one
                # particular button
                if not self.diag:
                    help_dialog(self.frame)
            if "S" in keys:
                focus = self.thePile.get_focus()
                if focus == self.wiredCB:
                    nettype = 'wired'
                    netname = self.wiredCB.original_widget.get_selected_profile()
                else:
                    nettype = 'wireless'
                    netname = str(self.wlessLB.get_focus()[1])
                run_configscript(self.frame, netname, nettype)
            if "O" in keys:
                exitcode, data = AdHocDialog().run(ui, self.frame)
                if exitcode == 1:
                    wireless.CreateAdHocNetwork(
                        data[0],
                        data[2],
                        data[1],
                        "WEP",
                        data[5],
                        data[4],
                        False
                    )
            if 'X' in keys:
                exitcode, data = ForgetDialog().run(ui, self.frame)
                if exitcode == 1:
                    text = _('Are you sure you want to discard settings for '
                        'the selected networks?')
                    text += '\n\n' + '\n'.join(data['essid'])
                    confirm, trash = TextDialog(text, 20, 50,
                        buttons=[(_('OK'), 1), (_('Cancel'), -1)],
                        ).run(ui, self.frame)
                    if confirm == 1:
                        for x in data['bssid']:
                            wireless.DeleteWirelessNetwork(x)

        for k in keys:
            if urwid.VERSION < (1, 0, 0):
                check_mouse_event = urwid.is_mouse_event
            else:
                check_mouse_event = urwid.util.is_mouse_event
            if check_mouse_event(k):
                event, button, col, row = k
                self.frame.mouse_event(
                    self.size, event, button, col, row, focus=True)
                continue
            k = self.frame.keypress(self.size, k)
            if self.diag:
                if  k == 'esc' or k == 'q' or k == 'Q':
                    self.restore_primary()
                    break
                # F10 has been changed to S to avoid using function keys,
                # which are often caught by the terminal emulator.
                # But F10 still works, because it doesn't hurt and some users might be used to it.
                if k == 'f10' or k == 'S' or k == 's':
                    self.diag.save_settings()
                    self.restore_primary()
                    break
            if k == "window resize":
                self.size = ui.get_cols_rows()
                continue

    def call_update_ui(self, source, cb_condition):
        """ Update UI. """
        self.update_ui(True)
        return True

    # Redraw the screen
    @wrap_exceptions
    def update_ui(self, from_key=False):
        if not ui._started:
            return False
        input_data = ui.get_input()
        self.handle_keys(input_data)
        canvas = self.frame.render((self.size), True)
        ui.draw_screen((self.size), canvas)
        if self.update_tag is not None:
            gobject.source_remove(self.update_tag)
        return False


    def connect(self, nettype, networkid, networkentry=None):
        """ Initiates the connection process in the daemon. """
        if nettype == "wireless":
            wireless.ConnectWireless(networkid)
        elif nettype == "wired":
            wired.ConnectWired()
        self.update_status()

def gen_network_list():
    wiredL = wired.GetWiredProfileList()
    wlessL = []
    for network_id in range(0, wireless.GetNumberOfNetworks()):
        is_active = wireless.GetCurrentSignalStrength("") != 0 and \
                    wireless.GetCurrentNetworkID(wireless.GetIwconfig()) == network_id and \
                    wireless.GetWirelessIP('') is not None
        label = NetLabel(network_id, is_active)
        wlessL.append(label)
    return (wiredL, wlessL)

def about_dialog(body):
    theText = [
        ('green', "   ///       \\\\\\"), "       _      ___        __\n",
        ('green', "  ///         \\\\\\"), "     | | /| / (_)______/ /\n",
        ('green', " ///           \\\\\\"), "    | |/ |/ / / __/ _  / \n",
        ('green', "/||  //     \\\\  ||\\"), "   |__/|__/_/\__/\_,_/  \n",
        ('green', "|||  ||"), "(|^|)", ('green', "||  |||"),
        "         ($VERSION)       \n".replace("$VERSION", daemon.Hello()),
        ('green', "\\||  \\\\"), " |+| ", ('green', "//  ||/    \n"),
        ('green', " \\\\\\"), "    |+|    ", ('green', "///"),
        "      http://launchpad.net/wicd\n",
        ('green', "  \\\\\\"), "   |+|   ", ('green', "///"), "      ",
        _('Brought to you by:'), "\n",
        ('green', "   \\\\\\"), "  |+|  ", ('green', "///"), "       * Tom Van Braeckel\n",
        "      __|+|__          * Adam Blackburn\n",
        "     ___|+|___         * Dan O'Reilly\n",
        "    ____|+|____        * Andrew Psaltis\n",
        "   |-----------|       * David Paleino\n"]
    about = TextDialog(theText, 18, 55, header=('header', _('About Wicd')))
    about.run(ui, body)

def help_dialog(body):
    textT = urwid.Text(('header', _('wicd-curses help')), 'right')
    textSH = urwid.Text([
        'This is ', ('blue', 'wicd-curses-' + CURSES_REV),
        ' using wicd ', str(daemon.Hello()), '\n'
    ])
    textH = urwid.Text([
        _('For more detailed help, consult the wicd-curses(8) man page.') + "\n",
        ('bold', '->'), ' and ', ('bold', '<-'),
        " are the right and left arrows respectively.\n"
    ])
    text1 = urwid.Text([
        ('bold', '  H h ?'), ": " + _('Display this help dialog') + "\n",
        ('bold', 'enter C'), ": " + _('Connect to selected network') + "\n",
        ('bold', '      D'), ": " + _('Disconnect from all networks') + "\n",
        ('bold', '    ESC'), ": " + _('Stop a connection in progress') + "\n",
        ('bold', '   F5 R'), ": " + _('Refresh network list') + "\n",
        ('bold', '      P'), ": " + _('Preferences dialog') + "\n",
    ])
    text2 = urwid.Text([
        ('bold', '      I'), ": " + _('Scan for hidden networks') + "\n",
        ('bold', '      S'), ": " + _('Select scripts') + "\n",
        ('bold', '      O'), ": " + _('Set up Ad-hoc network') + "\n",
        ('bold', '      X'), ": " + _('Remove settings for saved networks') + "\n",
        ('bold', '     ->'), ": " + _('Configure selected network') + "\n",
        ('bold', '      A'), ": " + _("Display 'about' dialog") + "\n",
        ('bold', ' F8 q Q'), ": " + _('Quit wicd-curses') + "\n",
    ])
    textF = urwid.Text(_('Press any key to return.'))
    blank = urwid.Text('')
    cols = urwid.Columns([text1, text2])
    pile = urwid.Pile([textH, cols])
    fill = urwid.Filler(pile)
    frame = urwid.Frame(fill, header=urwid.Pile([textT, textSH]), footer=textF)
    dim = ui.get_cols_rows()
    while True:
        ui.draw_screen(dim, frame.render(dim, True))
        keys = ui.get_input()
        mouse_release = False
        for k in keys:
            if urwid.VERSION < (1, 0, 0):
                check_mouse_event = urwid.is_mouse_event
            else:
                check_mouse_event = urwid.util.is_mouse_event
            if check_mouse_event(k) and k[0] == "mouse release":
                mouse_release = True
                break
        if mouse_release:
            continue
        if 'window resize' in keys:
            dim = ui.get_cols_rows()
        elif keys:
            break

def run_configscript(parent, netname, nettype):
    configfile = wpath.etc + netname + '-settings.conf'
    if nettype != 'wired':
        header = 'profile'
    else:
        header = 'BSSID'
    if nettype == 'wired':
        profname = nettype
    else:
        profname = wireless.GetWirelessProperty(int(netname), 'bssid')
    theText = [
        _('To avoid various complications, wicd-curses does not support directly '
          'editing the scripts. However, you can edit them manually. First, (as root), '
          'open the "$A" config file, and look for the section labeled by the $B in '
          'question. In this case, this is:').
        replace('$A', configfile).replace('$B', header),
        "\n\n[" + profname + "]\n\n",
        _('You can also configure the wireless networks by looking for the "[<ESSID>]" '
          'field in the config file.'),
        _('Once there, you can adjust (or add) the "beforescript", "afterscript", '
          '"predisconnectscript" and "postdisconnectscript" variables as needed, to '
          'change the preconnect, postconnect, predisconnect and postdisconnect scripts '
          'respectively.  Note that you will be specifying the full path to the scripts '
          '- not the actual script contents.  You will need to add/edit the script '
          'contents separately.  Refer to the wicd manual page for more information.')
    ]
    dialog = TextDialog(theText, 20, 80)
    dialog.run(ui, parent)

def check_for_wired(wired_ip, set_status):
    if wired_ip:
        set_status(_('Connected to wired network (IP: %s)') % wired_ip)
        return True
    return False

def check_for_wireless(iwconfig, wireless_ip, set_status):
    if wireless_ip:
        set_status(_('Connected to wireless network (IP: %s)') % wireless_ip)
        return True
    if 'off/any' not in iwconfig:
        return False
    return True

def gen_list_header():
    if daemon.GetSignalDisplayType() == 0:
        essidgap = 25
    else:
        essidgap = 28
    return 'C %s %*s %9s %17s %6s %s' % \
           ('STR ', essidgap, 'ESSID', 'ENCRYPT', 'BSSID', 'MODE', 'CHNL')

def handle_sigquit(signal_number, stack_frame):
    loop.quit()
    ui.stop()

class AdHocDialog(Dialog2):
    def __init__(self):
        essid_t = _('ESSID')
        ip_t = _('IP')
        channel_t = _('Channel')
        key_t = "    " + _('Key')
        use_ics_t = _('Activate Internet Connection Sharing')
        use_encrypt_t = _('Use Encryption (WEP only)')
        self.essid_edit = DynEdit(essid_t)
        self.ip_edit = DynEdit(ip_t)
        self.channel_edit = DynIntEdit(channel_t)
        self.key_edit = DynEdit(key_t, sensitive=False)
        self.use_ics_chkb = urwid.CheckBox(use_ics_t)
        self.use_encrypt_chkb = urwid.CheckBox(use_encrypt_t, on_state_change=self.encrypt_callback)
        blank = urwid.Text('')
        self.essid_edit.set_edit_text("My_Adhoc_Network")
        self.ip_edit.set_edit_text("169.254.12.10")
        self.channel_edit.set_edit_text("3")
        l = [self.essid_edit, self.ip_edit, self.channel_edit, blank,
             self.use_ics_chkb, self.use_encrypt_chkb, self.key_edit]
        body = urwid.ListBox(l)
        header = ('header', _('Create an Ad-Hoc Network'))
        Dialog2.__init__(self, header, 15, 50, body)
        self.add_buttons([(_('OK'), 1), (_('Cancel'), -1)])
        self.frame.set_focus('body')

    def encrypt_callback(self, chkbox, new_state, user_info=None):
        self.key_edit.set_sensitive(new_state)

    def unhandled_key(self, size, k):
        if k in ('up', 'page up'):
            self.frame.set_focus('body')
        if k in ('down', 'page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            self.frame.set_focus('footer')
            self.buttons.set_focus(0)
            self.view.keypress(size, k)

    def on_exit(self, exitcode):
        data = (self.essid_edit.get_edit_text(),
                self.ip_edit.get_edit_text().strip(),
                self.channel_edit.get_edit_text(),
                self.use_ics_chkb.get_state(),
                self.use_encrypt_chkb.get_state(),
                self.key_edit.get_edit_text())
        return exitcode, data

class ForgetDialog(Dialog2):
    def __init__(self):
        self.to_remove = dict(essid=[], bssid=[])
        header = urwid.AttrMap(urwid.Text('  %20s %20s' % ('ESSID', 'BSSID')), 'listbar')
        title = urwid.Text(_('Please select the networks to forget'))
        l = [title, header]
        for entry in wireless.GetSavedWirelessNetworks():
            label = '%20s %20s'
            if entry[1] != 'None':
                label = label % (entry[0], entry[1])
                data = entry
            else:
                label = label % (entry[0], 'global')
                data = (entry[0], 'essid:' + entry[0])
            cb = urwid.CheckBox(
                label,
                on_state_change=self.update_to_remove,
                user_data=data
            )
            l.append(cb)
        body = urwid.ListBox(l)
        header = ('header', _('List of saved networks'))
        Dialog2.__init__(self, header, 15, 50, body)
        self.add_buttons([(_('Remove'), 1), (_('Cancel'), -1)])
        self.frame.set_focus('body')

    def update_to_remove(self, widget, checked, data):
        if checked:
            self.to_remove['essid'].append(data[0])
            self.to_remove['bssid'].append(data[1])
        else:
            self.to_remove['essid'].remove(data[0])
            self.to_remove['bssid'].remove(data[1])

    def unhandled_key(self, size, k):
        if k in ('up', 'page up'):
            self.frame.set_focus('body')
        if k in ('down', 'page down'):
            self.frame.set_focus('footer')
        if k == 'enter':
            self.frame.set_focus('footer')
            self.buttons.set_focus(1)
            self.view.keypress(size, k)

    def on_exit(self, exitcode):
        return exitcode, self.to_remove

########################################
##### INITIALIZATION FUNCTIONS
########################################
def main():
    """ Main function. """
    global ui, loop
    misc.RenameProcess('wicd-curses')

    ui = urwid.raw_display.Screen()
    ui.register_palette([
        ('body', 'default', 'default'),
        ('focus', 'black', 'light gray'),
        ('header', 'light blue', 'default'),
        ('important', 'light red', 'default'),
        ('connected', 'dark green', 'default'),
        ('connected focus', 'black', 'dark green'),
        ('editcp', 'default', 'default', 'standout'),
        ('editbx', 'light gray', 'dark blue'),
        ('editfc', 'white', 'dark blue', 'bold'),
        ('editnfc', 'brown', 'default', 'bold'),
        ('tab active', 'dark green', 'light gray'),
        ('infobar', 'light gray', 'dark blue'),
        ('listbar', 'light blue', 'default'),
        ('green', 'dark green', 'default'),
        ('blue', 'light blue', 'default'),
        ('red', 'dark red', 'default'),
        ('bold', 'white', 'black', 'bold')
    ])
    signal.signal(signal.SIGQUIT, handle_sigquit)
    urwid.set_encoding('utf8')

    with ui.start():
        run()

def run():
    global loop
    loop = gobject.MainLoop()
    ui.set_mouse_tracking()
    app = appGUI()
    bus.add_signal_receiver(app.dbus_scan_finished, 'SendEndScanSignal', 'org.wicd.daemon.wireless')
    bus.add_signal_receiver(app.dbus_scan_started, 'SendStartScanSignal', 'org.wicd.daemon.wireless')
    bus.add_signal_receiver(app.update_netlist, 'StatusChanged', 'org.wicd.daemon')
    gobject.timeout_add(2000, app.update_status)
    fds = ui.get_input_descriptors()
    for fd in fds:
        gobject.io_add_watch(fd, gobject.IO_IN, app.call_update_ui)
    app.update_ui()  # Ensure UI is drawn initially
    loop.run()




# Mostly borrowed from gui.py
def setup_dbus(force=True):
    """ Initialize DBus. """
    global bus, daemon, wireless, wired
    try:
        dbusmanager.connect_to_dbus()
    except DBusException:
        print(_("Can't connect to the daemon, trying to start it automatically..."), file=sys.stderr)
    try:
        bus = dbusmanager.get_bus()
        dbus_ifaces = dbusmanager.get_dbus_ifaces()
        daemon = dbus_ifaces['daemon']
        wireless = dbus_ifaces['wireless']
        wired = dbus_ifaces['wired']
    except DBusException:
        print(_("Can't automatically start the daemon, this error is fatal..."), file=sys.stderr)
    if not daemon:
        print('Error connecting to wicd via D-Bus. '
              'Please make sure the wicd service is running.')
        sys.exit(3)
    netentry_curses.dbus_init(dbus_ifaces)
    return True


setup_dbus()

########################################
##### MAIN ENTRY POINT
########################################
if __name__ == '__main__':
    try:
        parser = OptionParser(
            version="wicd-curses-%s (using wicd %s)" %
                    (CURSES_REV, daemon.Hello()),
            prog="wicd-curses"
        )
    except Exception as e:
        if "DBus.Error.AccessDenied" in str(e):
            print(_('ERROR: wicd-curses was denied access to the wicd daemon: '
                    'please check that your user is in the "$A" group.'). \
                  replace('$A', '\033[1;34m' + wpath.wicd_group + '\033[0m'))
            sys.exit(1)
        else:
            raise
    (options, args) = parser.parse_args()
    main()
