Documentation
=============

* **Installing**
* `Using </using/>`_
* `Hacking </hacking/>`_
* `Features </features/>`_

Installing WeasyPrint
---------------------

WeasyPrint 0.3 depends on:

.. Note: keep this in sync with setup.py

* CPython 2.7
* Pango **>= 1.29.3** with GObject introspection
* PyGObject
* PyCairo
* PIL
* lxml
* cssutils >= 0.9.8
* CairoSVG

Unless you distribution already has a package for WeasyPrint, (the `Kozea
overlay`_ has one for Gentoo), we recommend that you install cssutils,
CairoSVG and WeasyPrint itself in a `virtualenv`_ with `pip`_,
and everything else with your distribution’s packages.

.. _Kozea overlay: https://github.com/Kozea/Overlay/blob/master/README
.. _pip: http://www.pip-installer.org/
.. _virtualenv: http://www.virtualenv.org/

On a Debian-based system: (Pango is recent enough in Debian Wheezy and
Ubuntu 11.10.)

.. code-block:: sh

    sudo apt-get install gir1.2-pango-1.0 python-gobject python-cairo python-imaging python-lxml

Then, in a virtualenv: (this will also pull cssutils and CairoSVG)

.. code-block:: sh

    source $MY_VIRTUALENV/bin/activate
    pip install WeasyPrint

If everything goes well, you’re ready to `start using </using/>`_ WeasyPrint!
Otherwise, please copy the exact error message before `asking for help
</community/>`_.

Supported Python interpreters
-----------------------------

Currently WeasyPrint is developed and tested on CPython 2.7 only. Earlier
or later (3.x) versions of Python may work with minor fixes, but this not
being worked on right now. `Contact us </community/>`_ if you’re interested.

Interpreters other than CPython (such as PyPy) are not supported, and won’t
be until we find a way to get the dependencies (see above) working there.
