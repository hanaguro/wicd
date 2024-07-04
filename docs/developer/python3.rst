Transformation to Python 3
==========================

Steps taken so far
------------------

- First step taken was rather straight forward conversion to
  python 3 syntax
- I tried to cleanup the project structure and make it more python
  like by separating different functions into different packages / modules
- I reworked the installer/setup script to make heavy use of
  `Python Setuptools`_ which is probably to most portable way to package
  python programms. This is still work in progress.

.. _Python Setuptools: https://setuptools.pypa.io


Todos
-----

This is an incomplete listing of things to do or to change 
which come to mind while working on wicd. It could be also 
a place to discuss upcoming topics

- Make resource file handling more python like. Traditionally,
  unix applications install their resource files in 
  `/usr/share/<application>`. However with `Python Setuptools`_
  resources files are typically installed within the python 
  package. This is especially important for the gtk app
  See subfolder `resources` in `wicd.frontends.gtk`. This not entirely
  working yet

- Clean up the project folders. Since restructuring the project
  to use python packages & modules, several leftover folders are
  dangling around which still contain some resource files. The files
  need to be reviewed if still needed and probably moved into
  "resources" folders within the pyhton packages as needed ore removed.

  
.. rubric:: Links
.. target-notes::