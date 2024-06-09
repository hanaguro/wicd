#!/usr/bin/env python3

""" configmanager -- Wicd configuration file manager

Wrapper around ConfigParser for wicd, though it should be
reusable for other purposes as well.

"""

#
#   Copyright (C) 2008-2009 Adam Blackburn
#   Copyright (C) 2008-2009 Dan O'Reilly
#   Copyright (C) 2011      David Paleino
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


import sys, os
import hashlib
import binascii
from configparser import RawConfigParser, ParsingError
import codecs

from wicd.misc import Noneify, to_unicode

from dbus import Int32

def psk_from_passphrase(passphrase, ssid):
    """Convert passphrase to PSK using SSID."""
    ssid = ssid.encode('utf-8')
    passphrase = passphrase.encode('utf-8')
    psk = hashlib.pbkdf2_hmac('sha1', passphrase, ssid, 4096, 32)
    return binascii.hexlify(psk).decode('utf-8')

def replace_apsk_value(network_config, apsk_value):
    """Replace the placeholder '$_APSK' with the actual value of 'apsk'."""
    if apsk_value and 'ssid' in network_config:
        psk_value = psk_from_passphrase(apsk_value, network_config['ssid'])
        for key, value in network_config.items():
            if isinstance(value, str) and '$_APSK' in value:
                print(f"Replacing $_APSK in {key}: {value} with {psk_value}")
                network_config[key] = value.replace('$_APSK', f'"{psk_value}"')  # 二重引用符で囲む
    return network_config

def sanitize_network_dict(network):
    sanitized = {}
    apsk_value = None

    # Check for apsk value
    for section, options in network.items():
        if isinstance(options, dict) and 'apsk' in options:
            apsk_value = options['apsk']

    for section, options in network.items():
        if isinstance(options, dict):
            sanitized[section] = {}
            for key, value in options.items():
                if key and value:
                    sanitized[section][key.strip()] = str(value).strip()
            # Replace $_APSK with actual apsk value
            if 'apsk' not in sanitized[section]:
                sanitized[section]['apsk'] = apsk_value  # apskを設定
            sanitized[section] = replace_apsk_value(sanitized[section], apsk_value)
        else:
            if section and options:
                sanitized[section.strip()] = str(options).strip()
    return sanitized


def sanitize_config_file(path):
    """ Remove invalid lines from config file. """
    print(f"Sanitizing config file: {path}")
    with open(path) as conf:
        newconf = ''.join(line for line in conf if '[' in line or '=' in line)
    with open(path, 'w') as conf:
        conf.write(newconf)
    print("Config file sanitized.")

class ConfigManager(RawConfigParser):
    """ A class that can be used to manage a given configuration file. """
    def __init__(self, path, debug=False, mark_whitespace="`'`"):
        RawConfigParser.__init__(self)
        self.config_file = path
        self.debug = debug
        self.mrk_ws = mark_whitespace
        if os.path.exists(path):
            sanitize_config_file(path)
        try:
            self.read(path)
        except ParsingError:
            self.write()
            try:
                self.read(path)
            except ParsingError as p:
                print(("Could not start wicd: %s" % p.message))
                sys.exit(1)

    def __repr__(self):
        return self.config_file

    def __str__(self):
        return self.config_file

    def get_config(self):
        """ Returns the path to the loaded config file. """
        return self.config_file

    def set_option(self, section, option, value, write=False):
        """ Wrapper around ConfigParser.set

        Adds the option to write the config file change right away.
        Also forces all the values being written to type str, and
        adds the section the option should be written to if it
        doesn't exist already.

        """
        if not self.has_section(section):
            self.add_section(section)
        if isinstance(value, str):
            value = to_unicode(value)
            if value.startswith(' ') or value.endswith(' '):
                value = "%(ws)s%(value)s%(ws)s" % {"value" : value,
                                                "ws" : self.mrk_ws}
        RawConfigParser.set(self, section, str(option), value)
        if write:
            self.write()

    def set(self, *args, **kargs):
        """ Calls the set_option method. """
        self.set_option(*args, **kargs)

    def get_option(self, section, option, default="__None__"):
        """ Wrapper around ConfigParser.get.

        Automatically adds any missing sections, adds the ability
        to write a default value, and if one is provided prints if
        the default or a previously saved value is returned.

        """
        if not self.has_section(section):
            if default != "__None__" and option != 'apsk':
                self.add_section(section)
            else:
                return None

        if self.has_option(section, option):
            ret = RawConfigParser.get(self, section, option)
            if (isinstance(ret, str) and ret.startswith(self.mrk_ws) 
                and ret.endswith(self.mrk_ws)):
                ret = ret[3:-3]
            ret = to_unicode(ret)
            if default:
                if self.debug:
                    # mask out sensitive information
                    if option in ['apsk', 'password', 'identity', \
                                'private_key', 'private_key_passwd', \
                                'key', 'passphrase']:
                        print((''.join(['found ', option, \
                            ' in configuration *****'])))
                    else:
                        print((''.join(['found ', option, ' in configuration ',
                                    str(ret)])))
        else:    # Use the default, unless no default was provided
            if default != "__None__" and option != 'apsk':
                print(('did not find %s in configuration, setting default %s' \
                    % (option, str(default))))
                self.set(section, option, str(default), write=True)
                ret = default
            else:
                ret = None

        # Try to intelligently handle the type of the return value.
        try:
            if not ret.startswith('0') or len(ret) == 1:
                ret = int(ret)
        except (ValueError, TypeError, AttributeError):
            ret = Noneify(ret)
        # This is a workaround for a python-dbus issue on 64-bit systems.
        if isinstance(ret, int):
            try:
                Int32(ret)
            except OverflowError:
                ret = str(ret)

        # ネットワーク辞書の正規化
        if option == 'apsk' and ret:
            network_config = {section: {option: ret}}
            ret = sanitize_network_dict(network_config)[section][option]

        return to_unicode(ret)

    def get(self, *args, **kargs):
        """ Calls the get_option method """
        return self.get_option(*args, **kargs)

    def _write_one(self):
        """ Writes the loaded config file to disk. """
        for section in self.sections():
            if not section:
                self.remove_section(section)
        with open(self.config_file, 'w') as configfile:
            RawConfigParser.write(self, configfile)

    def remove_section(self, section):
        """ Wrapper around the ConfigParser.remove_section() method.

        This method only calls the ConfigParser.remove_section() method
        if the section actually exists.

        """
        if self.has_section(section):
            RawConfigParser.remove_section(self, section)

    def reload(self):
        """ Re-reads the config file, in case it was edited out-of-band. """
        self.read(self.config_file)

    def read(self, path):
        """ Reads the config file specified by 'path' then reads all the
        files in the directory obtained by adding '.d' to 'path'. The files
        in the '.d' directory are read in normal sorted order and section
        entries in these files override entries in the main file.
        """
        if os.path.exists(path):
            RawConfigParser.readfp(self, codecs.open(path, 'r', 'utf-8'))

        path_d = path + ".d"
        files = []

        if os.path.exists(path_d):
            files = [ os.path.join(path_d, f) for f in os.listdir(path_d) ]
            files.sort()

        for fname in files:
            p = RawConfigParser()
            p.readfp(codecs.open(fname, 'r', 'utf-8'))
            for section_name in p.sections():
                # New files override old, so remove first to avoid
                # DuplicateSectionError.
                self.remove_section(section_name)
                self.add_section(section_name)
                for (name, value) in p.items(section_name):
                    self.set(section_name, name, value)
                # Store the filename this section was read from.
                self.set(section_name, '_filename_', fname)

    def _copy_section(self, name):
        """ Copy whole section from config file. """
        p = ConfigManager("", self.debug, self.mrk_ws)
        p.add_section(name)
        for (iname, value) in self.items(name):
            p.set(name, iname, value)
        # Store the filename this section was read from.
        p.config_file = p.get_option(name, '_filename_', p.config_file)
        p.remove_option(name, '_filename_')
        return p

    def write(self, fp=None):
        """ Writes the loaded config file to disk. """
        in_this_file = []
        sec_r = [to_unicode(s) for s in self.sections()]
        sec_r = [s for s in sec_r if s is not None]  # Remove None values
        for sname in sorted(sec_r):
            fname = self.get_option(sname, '_filename_')
            if fname and fname != self.config_file:
                # Write sections from other files
                section = self._copy_section(sname)
                section._write_one()
            else:
                # Save names of local sections
                in_this_file.append(sname)

        # Make an instance with only these sections
        p = ConfigManager("", self.debug, self.mrk_ws)
        p.config_file = self.config_file
        for sname in in_this_file:
            p.add_section(sname)
            for (iname, value) in self.items(sname):
                p.set(sname, iname, value)
            p.remove_option(sname, '_filename_')

        # ネットワーク辞書の正規化
        sanitized_network = sanitize_network_dict({s: dict(p.items(s)) for s in p.sections()})
        for section in sanitized_network:
            for key, value in sanitized_network[section].items():
                p.set(section, key, value)

        p._write_one()

