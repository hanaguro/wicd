import urwid
from curses_misc import DynWrap, MaskingEdit, ComboBox, error
import wicd.misc as misc
from wicd.misc import noneToString, stringToNone, noneToBlankString, to_bool

from wicd.translations import language, _
import os

daemon = None
wired = None
wireless = None

def dbus_init(dbus_ifaces):
    """ Initialize DBus interfaces. """
    global daemon, wired, wireless
    daemon = dbus_ifaces['daemon']
    wired = dbus_ifaces['wired']
    wireless = dbus_ifaces['wireless']

class AdvancedSettingsDialog(urwid.WidgetWrap):
    def __init__(self):
        self.ui = None
        self.body = None

        self.wired = None
        self.networkid = None

        self.encryption_info = None
        self.encryption_combo = None
        self.encrypt_types = None
        self.encryption_chkbox = None

        static_ip_t = _('Use Static IPs')
        ip_t = ('editcp', _('IP') + ':     ')
        netmask_t = ('editcp', _('Netmask') + ':')
        gateway_t = ('editcp', _('Gateway') + ':')

        use_static_dns_t = _('Use Static DNS')
        use_global_dns_t = _('Use global DNS servers')
        dns_dom_t = ('editcp', _('DNS domain') + ':   ')
        search_dom_t = ('editcp', _('Search domain') + ':')
        dns1_t = ('editcp', _('DNS server') + ' 1' + ':' + ' ' * 8)
        dns2_t = ('editcp', _('DNS server') + ' 2' + ':' + ' ' * 8)
        dns3_t = ('editcp', _('DNS server') + ' 3' + ':' + ' ' * 8)

        use_dhcp_h_t = _('Use DHCP Hostname')
        dhcp_h_t = ('editcp', _('DHCP Hostname') + ': ')

        cancel_t = _('Cancel')
        ok_t = _('OK')

        self.static_ip_cb = urwid.CheckBox(static_ip_t, on_state_change=self.static_ip_toggle)
        self.ip_edit = DynWrap(urwid.Edit(ip_t), False)
        self.netmask_edit = DynWrap(urwid.Edit(netmask_t), False)
        self.gateway_edit = DynWrap(urwid.Edit(gateway_t), False)

        self.static_dns_cb = DynWrap(urwid.CheckBox(use_static_dns_t, on_state_change=self.dns_toggle), True, ('body', 'editnfc'), None)
        self.global_dns_cb = DynWrap(urwid.CheckBox(use_global_dns_t, on_state_change=self.dns_toggle), False, ('body', 'editnfc'), None)
        self.checkb_cols = urwid.Columns([self.static_dns_cb, self.global_dns_cb])
        self.dns_dom_edit = DynWrap(urwid.Edit(dns_dom_t), False)
        self.search_dom_edit = DynWrap(urwid.Edit(search_dom_t), False)
        self.dns1 = DynWrap(urwid.Edit(dns1_t), False)
        self.dns2 = DynWrap(urwid.Edit(dns2_t), False)
        self.dns3 = DynWrap(urwid.Edit(dns3_t), False)

        self.use_dhcp_h = urwid.CheckBox(use_dhcp_h_t, False, on_state_change=self.use_dhcp_h_toggle)
        self.dhcp_h = DynWrap(urwid.Edit(dhcp_h_t), False)

        _blank = urwid.Text('')

        walker = urwid.SimpleListWalker([
            self.static_ip_cb,
            self.ip_edit,
            self.netmask_edit,
            self.gateway_edit,
            _blank,
            self.checkb_cols,
            self.dns_dom_edit,
            self.search_dom_edit,
            self.dns1, self.dns2, self.dns3,
            _blank,
            self.use_dhcp_h,
            self.dhcp_h,
            _blank
        ])

        self._listbox = urwid.ListBox(walker)
        self._frame = urwid.Frame(self._listbox)

        super().__init__(self._frame)

    def use_dhcp_h_toggle(self, checkb, new_state, user_data=None):
        """ Set sensitivity of widget. """
        self.dhcp_h.sensitive = new_state

    def static_ip_toggle(self, checkb, new_state, user_data=None):
        """ Set sensitivity of widget. """
        for w in [self.ip_edit, self.netmask_edit, self.gateway_edit]:
            w.sensitive = new_state
        self.static_dns_cb.original_widget.set_state(new_state)
        self.static_dns_cb.sensitive = not new_state
        self.checkb_cols.set_focus(self.global_dns_cb if new_state else self.static_dns_cb)

    def dns_toggle(self, checkb, new_state, user_data=None):
        """ Set sensitivity of widget. """
        if checkb == self.static_dns_cb.original_widget:
            for w in [self.dns_dom_edit, self.search_dom_edit, self.dns1, self.dns2, self.dns3]:
                w.sensitive = new_state
            if not new_state:
                self.global_dns_cb.original_widget.set_state(False, do_callback=False)
            self.global_dns_cb.sensitive = new_state
        if checkb == self.global_dns_cb.original_widget:
            for w in [self.dns_dom_edit, self.search_dom_edit, self.dns1, self.dns2, self.dns3]:
                w.sensitive = not new_state

    def set_net_prop(self, option, value):
        """ Set network property. MUST BE OVERRIDEN. """
        raise NotImplementedError

    def save_settings(self):
        if self.static_ip_cb.get_state():
            for i in [self.ip_edit, self.netmask_edit, self.gateway_edit]:
                i.set_edit_text(i.get_edit_text().strip())

            self.set_net_prop("ip", noneToString(self.ip_edit.get_edit_text()))
            self.set_net_prop("netmask", noneToString(self.netmask_edit.get_edit_text()))
            self.set_net_prop("gateway", noneToString(self.gateway_edit.get_edit_text()))
        else:
            self.set_net_prop("ip", '')
            self.set_net_prop("netmask", '')
            self.set_net_prop("gateway", '')

        if self.static_dns_cb.get_state() and not self.global_dns_cb.get_state():
            self.set_net_prop('use_static_dns', True)
            self.set_net_prop('use_global_dns', False)
            for i in [self.dns1, self.dns2, self.dns3, self.dns_dom_edit, self.search_dom_edit]:
                i.set_edit_text(i.get_edit_text().strip())
            self.set_net_prop('dns_domain', noneToString(self.dns_dom_edit.get_edit_text()))
            self.set_net_prop("search_domain", noneToString(self.search_dom_edit.get_edit_text()))
            self.set_net_prop("dns1", noneToString(self.dns1.get_edit_text()))
            self.set_net_prop("dns2", noneToString(self.dns2.get_edit_text()))
            self.set_net_prop("dns3", noneToString(self.dns3.get_edit_text()))
        elif self.static_dns_cb.get_state() and self.global_dns_cb.get_state():
            self.set_net_prop('use_static_dns', True)
            self.set_net_prop('use_global_dns', True)
        else:
            self.set_net_prop('use_static_dns', False)
            self.set_net_prop('use_global_dns', False)
            self.set_net_prop('dns_domain', '')
            self.set_net_prop("search_domain", '')
            self.set_net_prop("dns1", '')
            self.set_net_prop("dns2", '')
            self.set_net_prop("dns3", '')
        self.set_net_prop('dhcphostname', self.dhcp_h.get_edit_text())
        self.set_net_prop('usedhcphostname', self.use_dhcp_h.get_state())

    def ready_widgets(self, ui, body):
        """ Build comboboxes. """
        self.ui = ui
        self.body = body
        self.encryption_combo.build_combobox(body, ui, 14)
        self.change_encrypt_method()

    def combo_on_change(self, combobox, new_index, user_data=None):
        """ Handle change of item in the combobox. """
        self.change_encrypt_method()

    def change_encrypt_method(self):
        """ Change encrypt method based on combobox. """
        self.encryption_info = {}
        wid, ID = self.encryption_combo.get_focus()
        methods = self.encrypt_types

        if self._w.body.body.__contains__(self.pile_encrypt):
            self._w.body.body.pop(self._w.body.body.__len__() - 1)

        if ID == -1:
            self.encryption_combo.set_focus(0)
            ID = 0

        theList = []
        for type_ in ['required', 'optional']:
            fields = methods[ID][type_]
            for field in fields:
                try:
                    text = language[field[1].lower().replace(' ', '_')]
                except KeyError:
                    text = field[1].replace(' ', '_')
                edit = MaskingEdit(('editcp', text + ': '))
                edit.set_mask_mode('no_focus')
                theList.append(edit)
                self.encryption_info[field[0]] = [edit, type_]

                if self.wired:
                    edit.set_edit_text(noneToBlankString(wired.GetWiredProperty(field[0])))
                else:
                    edit.set_edit_text(noneToBlankString(wireless.GetWirelessProperty(self.networkid, field[0])))

        self.pile_encrypt = DynWrap(urwid.Pile(theList), attrs=('editbx', 'editnfc'))

        self.pile_encrypt.sensitive = self.encryption_chkbox.get_state()

        self._w.body.body.insert(self._w.body.body.__len__(), self.pile_encrypt)

    def encryption_toggle(self, chkbox, new_state, user_data=None):
        """ Set sensitivity of widget. """
        self.encryption_combo.sensitive = new_state
        self.pile_encrypt.sensitive = new_state

class WiredSettingsDialog(AdvancedSettingsDialog):
    def __init__(self, name, parent):
        AdvancedSettingsDialog.__init__(self)
        self.wired = True

        # prof_name のバリデーションを追加
        if name is None or not isinstance(name, str):
            # prof_name が None または文字列でない場合、デフォルト値を設定またはエラー処理
            self.prof_name = 'Default Profile'  # デフォルトのプロファイル名
            # エラー処理が必要な場合はここにログ記録や例外を投げる処理を追加
        else:
            self.prof_name = name

        title = _('Configuring preferences for wired profile "$A"').replace('$A', self.prof_name)
        self._w.header = urwid.Text(('header', title), align='right')

        self.set_default = urwid.CheckBox(_('Use as default profile (overwrites any previous default)'))
        self._listbox.body.append(self.set_default)

        self.parent = parent
        encryption_t = _('Use Encryption')

        self.encryption_chkbox = urwid.CheckBox(encryption_t, on_state_change=self.encryption_toggle)
        self.encryption_combo = ComboBox(callback=self.combo_on_change)
        self.pile_encrypt = None
        self._listbox.body.append(self.encryption_chkbox)
        self._listbox.body.append(self.encryption_combo)
        self.encrypt_types = misc.LoadEncryptionMethods(wired=True)
        self.set_values()


    def set_net_prop(self, option, value):
        wired.SetWiredProperty(option, str(value))

    def set_values(self):
        self.ip_edit.set_edit_text(self.format_entry("ip"))
        self.netmask_edit.set_edit_text(self.format_entry("netmask"))
        self.gateway_edit.set_edit_text(self.format_entry("gateway"))

        self.global_dns_cb.original_widget.set_state(bool(wired.GetWiredProperty('use_global_dns')))
        self.static_dns_cb.original_widget.set_state(bool(wired.GetWiredProperty('use_static_dns')))

        if stringToNone(self.ip_edit.get_edit_text()):
            self.static_ip_cb.set_state(True)
        self.dns1.set_edit_text(self.format_entry("dns1"))
        self.dns2.set_edit_text(self.format_entry("dns2"))
        self.dns3.set_edit_text(self.format_entry("dns3"))
        self.dns_dom_edit.set_edit_text(self.format_entry("dns_domain"))
        self.search_dom_edit.set_edit_text(self.format_entry("search_domain"))

        self.set_default.set_state(to_bool(wired.GetWiredProperty("default")))

        l = []
        activeID = -1
        for x, enc_type in enumerate(self.encrypt_types):
            l.append(enc_type['name'])
            if enc_type['type'] == wired.GetWiredProperty("enctype"):
                activeID = x
        self.encryption_combo.set_list(l)

        self.encryption_combo.set_focus(activeID)
        if wired.GetWiredProperty("encryption_enabled"):
            self.encryption_chkbox.set_state(True, do_callback=False)
            self.encryption_combo.sensitive = True
        else:
            self.encryption_combo.set_focus(0)
            self.encryption_combo.sensitive = False

        self.change_encrypt_method()

        dhcphname = wired.GetWiredProperty("dhcphostname")
        if dhcphname is None:
            dhcphname = os.uname()[1]

        self.use_dhcp_h.set_state(bool(wired.GetWiredProperty('usedhcphostname')))
        self.dhcp_h.sensitive = self.use_dhcp_h.get_state()
        self.dhcp_h.set_edit_text(str(dhcphname))

    def save_settings(self):
        if self.encryption_chkbox.get_state():
            encrypt_info = self.encryption_info
            encrypt_methods = self.encrypt_types
            self.set_net_prop("enctype", encrypt_methods[self.encryption_combo.get_focus()[1]]['type'])
            self.set_net_prop("encryption_enabled", True)
            for entry_info in list(encrypt_info.values()):
                if entry_info[0].get_edit_text() == "" and entry_info[1] == 'required':
                    # 修正部分: get_captionを削除し、captionプロパティを使用
                    error(self.ui, self.parent, "%s (%s)" % (_('Required encryption information is missing.'), entry_info[0].caption[0][0][0:-2]))
                    return False

            for entry_key, entry_info in list(encrypt_info.items()):
                self.set_net_prop(entry_key, noneToString(entry_info[0].get_edit_text()))
        else:
            self.set_net_prop("enctype", "None")
            self.set_net_prop("encryption_enabled", False)

        AdvancedSettingsDialog.save_settings(self)
        if self.set_default.get_state():
            wired.UnsetWiredDefault()
        if self.set_default.get_state():
            set_default = True
        else:
            set_default = False
        wired.SetWiredProperty("default", set_default)
        wired.SaveWiredNetworkProfile(self.prof_name)
        return True

    def format_entry(self, label):
        return noneToBlankString(wired.GetWiredProperty(label))

    def prerun(self, ui, dim, display):
        pass

class WirelessSettingsDialog(AdvancedSettingsDialog):
    def __init__(self, networkID, parent, ui):
        AdvancedSettingsDialog.__init__(self)
        self.wired = False

        self.bitrates = None

        self.networkid = networkID
        self.parent = parent
        self.ui = ui
        global_settings_t = _('Use these settings for all networks sharing this essid')
        encryption_t = _('Use Encryption')
        autoconnect_t = _('Automatically connect to this network')
        bitrate_t = _('Wireless bitrate')
        allow_lower_bitrates_t = _('Allow lower bitrates')

        self.global_settings_chkbox = urwid.CheckBox(global_settings_t)
        self.encryption_chkbox = urwid.CheckBox(encryption_t, on_state_change=self.encryption_toggle)
        self.encryption_combo = ComboBox(callback=self.combo_on_change)
        self.autoconnect_chkbox = urwid.CheckBox(autoconnect_t)
        self.bitrate_combo = ComboBox(bitrate_t)
        self.allow_lower_bitrates_chkbox = urwid.CheckBox(allow_lower_bitrates_t)

        self.pile_encrypt = None
        self._listbox.body.append(self.bitrate_combo)
        self._listbox.body.append(self.allow_lower_bitrates_chkbox)
        self._listbox.body.append(urwid.Text(''))
        self._listbox.body.append(self.global_settings_chkbox)
        self._listbox.body.append(self.autoconnect_chkbox)
        self._listbox.body.append(self.encryption_chkbox)
        self._listbox.body.append(self.encryption_combo)
        self.encrypt_types = misc.LoadEncryptionMethods()
        self.set_values()

        title = _('Configuring preferences for wireless network "$A" ($B)').replace('$A', wireless.GetWirelessProperty(networkID, 'essid')).replace('$B', wireless.GetWirelessProperty(networkID, 'bssid'))
        self._w.header = urwid.Text(('header', title), align='right')

    def set_values(self):
        networkID = self.networkid
        self.ip_edit.set_edit_text(self.format_entry(networkID, "ip"))
        self.netmask_edit.set_edit_text(self.format_entry(networkID, "netmask"))
        self.gateway_edit.set_edit_text(self.format_entry(networkID, "gateway"))

        self.global_dns_cb.original_widget.set_state(bool(wireless.GetWirelessProperty(networkID, 'use_global_dns')))
        self.static_dns_cb.original_widget.set_state(bool(wireless.GetWirelessProperty(networkID, 'use_static_dns')))

        if stringToNone(self.ip_edit.get_edit_text()):
            self.static_ip_cb.set_state(True)
        self.dns1.set_edit_text(self.format_entry(networkID, "dns1"))
        self.dns2.set_edit_text(self.format_entry(networkID, "dns2"))
        self.dns3.set_edit_text(self.format_entry(networkID, "dns3"))
        self.dns_dom_edit.set_edit_text(self.format_entry(networkID, "dns_domain"))
        self.search_dom_edit.set_edit_text(self.format_entry(networkID, "search_domain"))

        self.autoconnect_chkbox.set_state(to_bool(self.format_entry(networkID, "automatic")))

        self.bitrates = wireless.GetAvailableBitrates()
        self.bitrates.append('auto')
        self.bitrate_combo.set_list(self.bitrates)

        bitrate = wireless.GetWirelessProperty(networkID, 'bitrate')
        if bitrate in self.bitrates:
            self.bitrate_combo.set_focus(self.bitrates.index(bitrate))
        else:
            self.bitrate_combo.set_focus(self.bitrates.index('auto'))

        self.allow_lower_bitrates_chkbox.set_state(to_bool(self.format_entry(networkID, 'allow_lower_bitrates')))

        self.encryption_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID, 'encryption')), do_callback=False)
        self.global_settings_chkbox.set_state(bool(wireless.GetWirelessProperty(networkID, 'use_settings_globally')))

        l = []
        activeID = -1
        for x, enc_type in enumerate(self.encrypt_types):
            l.append(enc_type['name'])
            if enc_type['type'] == wireless.GetWirelessProperty(networkID, "enctype"):
                activeID = x
        self.encryption_combo.set_list(l)
        self.encryption_combo.build_overlay(self.ui, self._listbox.body)
        self.encryption_combo.set_focus(activeID)
        if activeID != -1:
            self.encryption_chkbox.set_state(True, do_callback=False)
            self.encryption_combo.sensitive = True
        else:
            self.encryption_combo.set_focus(0)

        # 現在の画面サイズを取得
        size = self.ui.get_cols_rows()
        # 現在のフレームからキャンバスを生成
        canvas = self._frame.render(size, True)
        # 画面を更新
        self.ui.draw_screen(size, canvas)

        self.change_encrypt_method()
        dhcphname = wireless.GetWirelessProperty(networkID, "dhcphostname")
        if dhcphname is None:
            dhcphname = os.uname()[1]
        self.use_dhcp_h.set_state(bool(wireless.GetWirelessProperty(networkID, 'usedhcphostname')))
        self.dhcp_h.sensitive = self.use_dhcp_h.get_state()
        self.dhcp_h.set_edit_text(str(dhcphname))

    def set_net_prop(self, option, value):
        wireless.SetWirelessProperty(self.networkid, option, str(value))

    def format_entry(self, networkid, label):
        return noneToBlankString(wireless.GetWirelessProperty(networkid, label))

    def save_settings(self):
        if self.encryption_chkbox.get_state():
            encrypt_info = self.encryption_info
            encrypt_methods = self.encrypt_types
            self.set_net_prop("enctype", encrypt_methods[self.encryption_combo.get_focus()[1]]['type'])
            for entry_info in list(encrypt_info.values()):
                if entry_info[0].get_edit_text() == "" and entry_info[1] == 'required':
                    error(self.ui, self.parent, "%s (%s)" % (_('Required encryption information is missing.'), entry_info[0].caption[0][0][0:-2]))
                    return False

            for entry_key, entry_info in list(encrypt_info.items()):
                if entry_key == 'apsk':
                    # Ensure psk is not double quoted
                    self.set_net_prop(entry_key, entry_info[0].get_edit_text().strip('"'))
                else:
                    self.set_net_prop(entry_key, noneToString(entry_info[0].get_edit_text()))
        else:
            self.set_net_prop("enctype", "None")
            self.set_net_prop("encryption_enabled", False)
        AdvancedSettingsDialog.save_settings(self)

        self.set_net_prop("automatic", self.autoconnect_chkbox.get_state())

        if self.global_settings_chkbox.get_state():
            self.set_net_prop('use_settings_globally', True)
        else:
            self.set_net_prop('use_settings_globally', False)
            wireless.RemoveGlobalEssidEntry(self.networkid)

        self.set_net_prop('bitrate', self.bitrates[self.bitrate_combo.get_focus()[1]])
        self.set_net_prop('allow_lower_bitrates', self.allow_lower_bitrates_chkbox.get_state())
        wireless.SaveWirelessNetworkProfile(self.networkid)
        return True

    def ready_widgets(self, ui, body):
        AdvancedSettingsDialog.ready_widgets(self, ui, body)
        self.ui = ui
        self.body = body
        self.bitrate_combo.build_combobox(body, ui, 17)
