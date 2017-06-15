Installing
==========

WeasyPrint |version| depends on:

* CPython_ 2.7 or ≥ 3.3
* cairo_ [#]_
* Pango_
* CFFI_ ≥ 0.6
* lxml_ ≥ 3.0
* html5lib_ ≥ 0.999999999
* cairocffi_ ≥ 0.5
* tinycss2_ ≥ 0.5
* cssselect_ ≥ 0.6
* CairoSVG_ ≥ 1.0.20
* Pyphen_ ≥ 0.8
* Optional: GDK-PixBuf_ [#]_

.. _CPython: http://www.python.org/
.. _cairo: http://cairographics.org/
.. _Pango: http://www.pango.org/
.. _CFFI: https://cffi.readthedocs.org/
.. _html5lib: http://html5lib.readthedocs.org/
.. _cairocffi: http://pythonhosted.org/cairocffi/
.. _lxml: http://lxml.de/
.. _tinycss2: http://packages.python.org/tinycss2/
.. _cssselect: http://packages.python.org/cssselect/
.. _CairoSVG: http://cairosvg.org/
.. _Pyphen: https://github.com/Kozea/Pyphen
.. _GDK-PixBuf: https://live.gnome.org/GdkPixbuf


Python, cairo, Pango and GDK-PixBuf need to be installed separately. See
platform-specific instructions for :ref:`Linux <linux>`, :ref:`OS X <os-x>` and
:ref:`Windows <windows>` below.

lxml can be installed by pip automatically if your system has a C compiler and
the recursive dependencies, but using a system package might be easier.

Install WeasyPrint with pip_.
This will automatically install most of dependencies.
You probably need either virtualenv_ [#]_ (recommended) or using ``sudo``.

.. _virtualenv: http://www.virtualenv.org/
.. _pip: http://pip-installer.org/

.. code-block:: sh

    virtualenv --system-site-packages ./venv
    . ./venv/bin/activate
    pip install WeasyPrint

Now let’s try it:

.. code-block:: sh

    weasyprint --help
    weasyprint http://weasyprint.org ./weasyprint-website.pdf

You should see warnings about unsupported CSS 3 stuff; this is expected.
In the PDF you should see the WeasyPrint logo on the first page.

You can also play with :ref:`navigator`. Start it with

.. code-block:: sh

    python -m weasyprint.navigator

and open your browser at http://127.0.0.1:5000/. Read more :ref:`in the tutorial <navigator>`.

If everything goes well, you’re ready to :doc:`start using </tutorial>`
WeasyPrint! Otherwise, please copy the full error message and
`report the problem <http://weasyprint.org/community/>`_.

.. [#] cairo ≥ 1.12 is best but older versions should work too.
       The test suite passes on cairo 1.8 and 1.10 with some tests marked as
       “expected failures” due to behavior changes or bugs in cairo.

.. [#] Without it, PNG and SVG are the only supported image format:
       JPEG, GIF and others are not available.

.. [#] Passing the ``--system-site-packages`` option to virtualenv
       allows the environment to use the system packages for lxml,
       but this is not necessary if you install them with pip.


Linux
-----

Pango, GdkPixbuf, and cairo can not be installed
with pip and need to be installed from your platform’s packages.
lxml and CFFI can, but you’d still need their own dependencies.
This section lists system packages for lxml and CFFI when available,
the dependencies otherwise.
lxml needs *libxml2* and *libxslt*, CFFI needs *libffi*.
On Debian, the package names with development files are
``libxml2-dev``, ``libxslt1-dev`` and ``libffi-dev``.

You should use Python 3 instead of Python 2. Seriously.

If your favorite system is not listed here but you know the package names,
`tell us <http://weasyprint.org/community/>`_ so we can add it here.

Debian / Ubuntu
~~~~~~~~~~~~~~~

Ubuntu 16.04 Xenial or newer:

.. code-block:: sh

    sudo apt-get install python3-dev python3-pip python3-lxml python3-cffi libcairo2 libpango1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

Debian 8.0 Jessie or newer, Ubuntu 14.04 Trusty or newer:

.. code-block:: sh

    sudo apt-get install python-dev python-pip python-lxml python-cffi libcairo2 libpango1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

Debian 7.0 Wheezy or newer, Ubuntu 12.04 Precise or newer:

.. code-block:: sh

    sudo apt-get install python-dev python-pip python-lxml libcairo2 libpango1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

Fedora
~~~~~~

WeasyPrint is `packaged for Fedora
<https://apps.fedoraproject.org/packages/weasyprint>`_, but you can install it
with pip after installing the following packages:

.. code-block:: sh

    sudo yum install redhat-rpm-config python-devel python-pip python-lxml python-cffi libffi-devel cairo pango gdk-pixbuf2

Archlinux
~~~~~~~~~

WeasyPrint is `available in the AUR
<https://aur.archlinux.org/packages/python-weasyprint/>`_, but you can install
it with pip after installing the following packages:

.. code-block:: sh

    sudo pacman -S python-pip python-lxml cairo pango gdk-pixbuf2 libffi pkg-config

Gentoo
~~~~~~

WeasyPrint is `packaged in Gentoo
<https://packages.gentoo.org/packages/dev-python/weasyprint>`_, but you can
install it with pip after installing the following packages:

.. code-block:: sh

    emerge pip cairo pango gdk-pixbuf cffi lxml


OS X
----

WeasyPrint is automatically installed and tested on virtual MacOS machines. The
official installation method relies on Homebrew:

.. code-block:: sh

    brew install python3 cairo pango gdk-pixbuf libxml2 libxslt libffi

Don't forget to use the `pip3` command to install WeasyPrint, as `pip` may be
using the version of Python installed with MacOS.

You can also try with Macports, but please notice that this solution is not
tested and thus not recommended (**also known as "you're on your own and may
end up crying blood with sad dolphins for eternity"**):

.. code-block:: sh

    sudo port install py-pip py-lxml cairo pango gdk-pixbuf2 libffi


Windows
-------

Dear Windows user, please follow these steps carefully.

Really carefully. Don't cheat.

**If you decide to install Python, GTK or lxml 32 bit on Windows 64 bit, you're
on your own, don't even try to report an issue, kittens will die because of
you.**

- Install `Python 3.6.x <https://www.python.org/downloads/release/python>`_
  **with "Add Python 3.6 to PATH" checked**:

  - "Windows x86 executable installer" on Windows 32 bit,
  - "Windows x86-64 executable installer" on Windows 64 bit,

- install GTK **with "Set up PATH environment variable to include GTK+"
  checked**:

  - on Windows 32 bit: `gtk2-runtime-x.x.x-x-x-x-ash.exe
    <http://gtk-win.sourceforge.net/home/index.php/Main/Downloads>`_,
  - on Windows 64 bit: `gtk3-runtime-x.x.x-x-x-x-ts-win64.exe
    <https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer>`_,

- reboot,
- install `Visual C++ Build Tools
  <https://landinghub.visualstudio.com/visual-cpp-build-tools>`_ as explained
  in `Python's wiki <https://wiki.python.org/moin/WindowsCompilers>`_,
- download `lxml for Windows <http://www.lfd.uci.edu/~gohlke/pythonlibs/#lxml>`_:

  - "lxml-x.x.x-cp36-cp36m-win32.whl" on Windows 32 bit,
  - "lxml-x.x.x-cp36-cp36m-win_amd64.whl" on Windows 64 bit,

- install lxml with ``python -m pip install path/to/lxml-xxx.whl``
- install WeasyPrint with ``python -m pip install weasyprint``,
- test with ``python -m weasyprint http://weasyprint.org weasyprint.pdf``.
