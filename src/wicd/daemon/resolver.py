
#!/usr/bin/env python3
# vim: set fileencoding=utf8
#
#   wicd dns resolver manager
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
import wicd.config
import wicd.misc
import os
import atexit

class ResolverManager(object):
    _manager = None

    def __new__(cls):
        if cls._manager:
            return cls._manager
        elif cls == ResolverManager:
            try:
                return ResolvConfToolRunner()
            except ValueError:
                return ResolvConfUpdater()
        else:
            return super().__new__(cls)

    def __init__(self):
        ResolverManager._manager = self
        

get_manager = ResolverManager

class ResolvConfUpdater(ResolverManager):
    u''' Directly updates /etc/resolv.conf as needed '''

    resolvconf_backed = False
        
    def get_resolv_params(dns1=None, dns2=None, dns3=None, dns_dom=None, search_dom=None):
        resolv_params = ""
        if dns_dom:
            resolv_params += 'domain %s\n' % dns_dom
        if search_dom:
            resolv_params += 'search %s\n' % search_dom

        valid_dns_list = []
        for dns in (dns1, dns2, dns3):
            if dns:
                if wicd.misc.IsValidIP(dns):
                    if self.verbose:
                        print('Setting DNS : ' + dns)
                    valid_dns_list.append("nameserver %s\n" % dns)
                else:
                    print('DNS IP %s is not a valid IP address, skipping' % dns)

        if valid_dns_list:
            resolv_params += ''.join(valid_dns_list)

        return resolv_params

    def backup_resolvconf(self):
        if self.resolvconf_backed:
            return

        orig_path   = wicd.config.resolvconf_path
        backup_path = wicd.config.resolvconf_backup_path

        if os.path.islink(orig_path):
            dest = os.readlink(orig_path)
            def restore_resolvconf():
                os.remove(orig_path)
                os.symlink(dest, orig_path)
        else:
            # Don't back up if the backup already exists, either as a regular file or a symlink
            # The backup file should have been cleaned up by wicd, so perhaps it didn't exit cleanly.
            if not os.path.exists(backup_path):
                with open(orig_path, 'rb') as orig, open(backup_path, 'wb') as backup:
                    backup.write(orig.read())
                os.chmod(backup_path, 0o644)

            def restore_resolvconf():
                os.replace(backup_path, orig_path)

        atexit.register(restore_resolvconf)
        self.resolvconf_backed = True

    def set_dns(self, iface, **kw):
        self.backup_resolvconf()
        
        with open(wicd.config.resolvconf_path, "wt") as f:
            f.write(resolv_params + "\n")

class ResolvConfToolRunner(ResolvConfUpdater):
    u''' Uses resolvconf tool to manage dns '''

    tool = "resolvconf"

    def __new__(cls):
        inst = super().__new__(cls)

        if inst != cls._manager:
            inst.tool_path = wicd.misc.find_path(cls.tool)

            if not inst.tool_path:
                raise ValueError(u'Tool {} not found'.format(cls.tool))

        return inst

    def set_dns(self, iface, **kw):
        resolv_params = self.get_resolv_params(**kw)

        cmd = [self.tool_path, '-a', iface + '.wicd']
        p = wicd.misc.Run(cmd, include_stderr=True, return_obj=True)
        p.communicate(input=resolv_params)
