Development Testing
===================

wicd consists of a daemon running in background with root permissions
and a user interface client executing with user permissions. In addition
the daemon will fidle with various network settings and configuration
files. This complicates testing a bit. See the next sections for
some possibilities.

User Interface only tests
-------------------------

Assuming that a wicd daemon is installed and running with proper 
system permissions and that the dbus api of the installed wicd daemon
and the user client to test are compatible, it is possible to just run
the wicd client application from this project directory. The client 
will connect with the wicd daemon of the system but use the source 
code from the project directory. For this, the gtk client is started as 
follows::

   /wicd$ PYTHONPATH=src python3 -m wicd.frontends.gtk

while the command line tool can be executed with::

   /wicd$ PYTHONPATH=src python3 -m wicd.frontends.cli

This method allows to test changes to python code within namespace
`wicd.frontends`. 

.. warning::

   Although its a user interface test only, the user client will 
   communicate with the system's wicd daemon.  Thus it may 
   alter or even destroy your entire networking configuration
   during testing

Tests with user permissions
---------------------------

wicd daemon can be run with user permissions to prevent it
from altering system configuration or changing network settings.
This is the safest test mode but its also limited to "read-only"
functionality. For this the wicd daemon has to be run as user
and it has to use the *session dbus* instead of the system dbus.
Also, the daemon has to use a fake path configuration to place 
configuration & status files to. For that purpose, the project 
contains the special directory `tests` which will inject
test configuration. (See file `tests/wicd/config.py`)

wicd daemon can then run in foreground using a separate terminal::

   /wicd$ PYTHONPATH="tests:src" python3 -m wicd.daemon --session-dbus -f

The above test configuration will create a folder `devel_tmp` within
the project folder to hold the runtime files. Terminate wicd daemon
with `[Ctrl+C]`. While the daemon is running, a client to
connect with it can be started with::

   /wicd$ PYTHONPATH=src python3 -m wicd.frontends.gtk --session-dbus

.. tip::

   While this test mode can not adjust network configuration, its
   the safest method to test your changes wihtout fear to destroy
   your network config.

Tests with root permissions
---------------------------

.. caution::

   Letting wicd daemon run with root permission for test may alter your 
   entire network configuration at once with persistence over reboots.
   You might lock out yourself from any network access. BE CAREFUL!

Testing wicd daemon from the project directory and running it with root 
permissions be a bit tricky. You can not use `session dbus` since dbus will
refuse another user (root) to connect to the users session dbus. Instead
you have to run the daemon using the system dbus which means:

* you need to stop any system wicd daemon
* you need to setup security policies of dbus to allow the wicd from
  your project directory to own service `org.wicd.daemon`

If that is done, wicd can be started with root permissions, and if possible
should be still confined to the project folder::

   /wicd$ sudo PYTHONPATH="tests:src" python3 -m wicd.daemon -f

Afterwards, the client application can run with user permissions as 
explained in :ref:`User Interface only tests`

