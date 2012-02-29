Documentation
=============

* **Installing**
* `Using </using/>`_
* `Hacking </hacking/>`_
* `Features </features/>`_

Installing WeasyPrint
---------------------

WeasyPrint 0.6 depends on:

.. Note: keep this in sync with setup.py

* CPython 2.6, 2.7 or 3.2
* Pango **>= 1.29.3** with GObject introspection
* PyGObject
* PyCairo
* lxml
* pystacia
* cssutils >= 0.9.9
* CairoSVG >= 0.3

Unless you distribution already has a package for WeasyPrint, (the `Kozea
overlay`_ has one for Gentoo), we recommend that you install pystacia,
cssutils, CairoSVG and WeasyPrint itself in a `virtualenv`_ with `pip`_,
and everything else with your distribution’s packages.

.. _Kozea overlay: https://github.com/Kozea/Overlay/blob/master/README
.. _pip: http://www.pip-installer.org/
.. _virtualenv: http://www.virtualenv.org/

On a Debian-based system: (Pango is recent enough in Debian Wheezy and
Ubuntu 11.10.)

.. code-block:: sh

    sudo apt-get install gir1.2-pango-1.0 python-gobject python-cairo python-lxml imagemagick

Then, in a virtualenv: (this will also pull pystacia, cssutils and CairoSVG)

.. code-block:: sh

    source $MY_VIRTUALENV/bin/activate
    pip install WeasyPrint

If everything goes well, you’re ready to `start using </using/>`_ WeasyPrint!
Otherwise, please copy the exact error message before `asking for help
</community/>`_.
