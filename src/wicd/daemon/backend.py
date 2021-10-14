#!/usr/bin/env python3

""" Backend manager for wicd.

Manages and loads the pluggable backends for wicd.

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
import pkg_resources

import sys
import os

def fail(backend_name, reason):
    """ Helper to warn the user about failure in loading backend. """
    print(("Failed to load backend %s: %s" % (backend_name, reason)))
    return True


class BackendManager(object):
    """ Manages, validates, and loads wicd backends. """

    NoneBackend = type("NoBackend", tuple(), {
        "NAME" : None,
        "UPDATE_INTERVAL" : None,
        "DESCRIPTION" : "Not available",
    })

    the_backend = NoneBackend()

    def _valid_backend_file(self, be_file):
        """ Make sure the backend file is valid. """
        return (os.path.exists(be_file) and 
                os.path.basename(be_file).startswith("be-") and
                be_file.endswith(".py"))
    
    def get_current_backend(self):
        return self.the_backend.NAME
    
    def get_available_backends(self):
        return [entry_point.name for entry_point in pkg_resources.iter_entry_points('wicd.backends')]
    
    def get_update_interval(self):
        return self.the_backend.UPDATE_INTERVAL
        
    def get_backend_description(self, backend_name):
        """ Loads a backend and returns its description. """
        return self._load_backend(backend_name).DESCRIPTION
    
    @classmethod
    def _load_backend(cls, backend_name):
        """ Imports a backend and returns the loaded module. """
        for entry_point in pkg_resources.iter_entry_points('wicd.backends'):
            if entry_point.name == backend_name:
                return entry_point.load()
        
        return cls.NoneBackend()
            
    def load_backend(self, backend_name):
        """ Load and return a backend module. 
        
        Given a backend name be-foo, attempt to load a python module
        in the backends directory called be-foo.py.  The module must
        include a certain set of classes and variables to be considered
        valid.
        
        """
        self.the_backend = backend = self._load_backend(backend_name)
        print(('successfully loaded backend %s' % backend.NAME))
        return backend
