Installing
==========

WeasyPrint |version| depends on:

* CPython_ ≥ 3.5.0
* cairo_ ≥ 1.15.4 [#]_
* Pango_ ≥ 1.38.0 [#]_
* setuptools_ ≥ 30.3.0 [#]_
* CFFI_ ≥ 0.6
* html5lib_ ≥ 0.999999999
* cairocffi_ ≥ 0.9.0
* tinycss2_ ≥ 0.5
* cssselect2_ ≥ 0.1
* CairoSVG_ ≥ 1.0.20
* Pyphen_ ≥ 0.8
* GDK-PixBuf_ ≥ 2.25.0 [#]_

.. _CPython: http://www.python.org/
.. _cairo: http://cairographics.org/
.. _Pango: http://www.pango.org/
.. _setuptools: https://pypi.org/project/setuptools/
.. _CFFI: https://cffi.readthedocs.io/
.. _html5lib: https://html5lib.readthedocs.io/
.. _cairocffi: https://cairocffi.readthedocs.io/
.. _tinycss2: https://tinycss2.readthedocs.io/
.. _cssselect2: https://cssselect2.readthedocs.io/
.. _CairoSVG: http://cairosvg.org/
.. _Pyphen: http://pyphen.org/
.. _GDK-PixBuf: https://live.gnome.org/GdkPixbuf


Python, cairo, Pango and GDK-PixBuf need to be installed separately. See
platform-specific instructions for :ref:`Linux <linux>`, :ref:`macOS <macos>`
and :ref:`Windows <windows>` below.

Install WeasyPrint with pip_. This will automatically install most of
dependencies. You probably need either a virtual environment (venv,
recommended) or using ``sudo``.

.. _pip: http://pip-installer.org/

.. code-block:: sh

    python3 -m venv ./venv
    . ./venv/bin/activate
    pip install WeasyPrint

Now let’s try it:

.. code-block:: sh

    weasyprint --help
    weasyprint http://weasyprint.org ./weasyprint-website.pdf

You should see warnings about unsupported CSS 3 stuff; this is expected.
In the PDF you should see the WeasyPrint logo on the first page.

You can also play with :ref:`navigator` or :ref:`renderer`. Start it with

.. code-block:: sh

    python -m weasyprint.tools.navigator

or

.. code-block:: sh

    python -m weasyprint.tools.renderer

and open your browser at http://127.0.0.1:5000/.

If everything goes well, you’re ready to :doc:`start using </tutorial>`
WeasyPrint! Otherwise, please copy the full error message and
`report the problem <https://github.com/Kozea/WeasyPrint/issues/>`_.

.. [#] cairo ≥ 1.15.4 is best but older versions may work too. The test suite
       passes on cairo 1.14, and passes with some tests marked as “expected
       failures” on 1.10 and 1.12 due to behavior changes or bugs in cairo. If
       you get incomplete SVG renderings, please read `#339
       <https://github.com/Kozea/WeasyPrint/issues/339>`_. If you get invalid
       PDF files, please read `#565
       <https://github.com/Kozea/WeasyPrint/issues/565>`_. Some PDF metadata
       including PDF information, hyperlinks and bookmarks require 1.15.4.

.. [#] pango ≥ 1.29.3 is required, but 1.38.0 is needed to handle `@font-face`
       CSS rules.

.. [#] setuptools ≥ 30.3.0 is required to install WeasyPrint from wheel, but
       39.2.0 is required to build the package or install from
       source. setuptools < 40.8.0 will not include the LICENSE file.

.. [#] Without it, PNG and SVG are the only supported image formats.
       JPEG, GIF and others are not available.


.. _linux:

Linux
-----

Pango, GdkPixbuf, and cairo can not be installed
with pip and need to be installed from your platform’s packages.
CFFI can, but you’d still need their own dependencies.
This section lists system packages for CFFI when available,
the dependencies otherwise.
CFFI needs *libffi* with development files. On Debian, the package is called
``libffi-dev``.

If your favorite system is not listed here but you know the package names,
`tell us <http://weasyprint.org/about/>`_ so we can add it here.

Debian / Ubuntu
~~~~~~~~~~~~~~~

Debian 9.0 Stretch or newer, Ubuntu 16.04 Xenial or newer:

.. code-block:: sh

    sudo apt-get install build-essential python3-dev python3-pip python3-setuptools python3-wheel python3-cffi libcairo2 libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0 libffi-dev shared-mime-info

Fedora
~~~~~~

WeasyPrint is `packaged for Fedora
<https://apps.fedoraproject.org/packages/weasyprint>`_, but you can install it
with pip after installing the following packages:

.. code-block:: sh

    sudo yum install redhat-rpm-config python-devel python-pip python-setuptools python-wheel python-cffi libffi-devel cairo pango gdk-pixbuf2

Archlinux
~~~~~~~~~

WeasyPrint is `available in the AUR
<https://aur.archlinux.org/packages/python-weasyprint/>`_, but you can install
it with pip after installing the following packages:

.. code-block:: sh

    sudo pacman -S python-pip python-setuptools python-wheel cairo pango gdk-pixbuf2 libffi pkg-config

Gentoo
~~~~~~

WeasyPrint is `packaged in Gentoo
<https://packages.gentoo.org/packages/dev-python/weasyprint>`_, but you can
install it with pip after installing the following packages:

.. code-block:: sh

    emerge pip setuptools wheel cairo pango gdk-pixbuf cffi


Alpine
~~~~~~

For Alpine Linux 3.6 or newer:

.. code-block:: sh

    apk --update --upgrade add gcc musl-dev jpeg-dev zlib-dev libffi-dev cairo-dev pango-dev gdk-pixbuf-dev

.. note::

    Some Alpine images do not resolv the library path via ctypes.utils.find_library. So if you get
    ``OSError: dlopen() failed to load a library: cairo / cairo-2 / cairo-gobject-2``
    then change find_library and open the library directly:
    ``/usr/local/lib/python3.7/site-packages/cairocffi/__init__.py``

    .. code-block:: python

        try:
            lib = ffi.dlopen(name)
            if lib:
        ...
        cairo = dlopen(ffi, 'libcairo.so.2')


.. _macos:

macOS
-----

WeasyPrint is automatically installed and tested on virtual macOS machines. The
official installation method relies on Homebrew:

.. code-block:: sh

    brew install python3 cairo pango gdk-pixbuf libffi

Don't forget to use the `pip3` command to install WeasyPrint, as `pip` may be
using the version of Python installed with macOS.

If you get the `Fontconfig error: Cannot load default config file` message,
then try reinstalling fontconfig with the `universal` option:

.. code-block:: sh

    brew uninstall fontconfig
    brew install fontconfig --universal

You can also try with Macports, but please notice that this solution is not
tested and thus not recommended (**also known as "you're on your own and may
end up crying blood with sad dolphins for eternity"**):

.. code-block:: sh

    sudo port install py-pip cairo pango gdk-pixbuf2 libffi


.. _windows:

Windows
-------

Dear Windows user, please follow these steps carefully.

Really carefully. Don’t cheat.

Besides a proper Python installation and a few Python packages, WeasyPrint
needs the Pango, cairo and GDK-PixBuf libraries. They are required for the
graphical stuff: Text and image rendering.  These libraries aren't Python
packages. They are part of `GTK+ <https://en.wikipedia.org/wiki/GTK+>`_
(formerly known as GIMP Toolkit), and must be installed separately.

The following installation instructions for the GTK+ libraries don't work on
Windows XP. That means: Windows Vista or later is required.

Of course you can decide to install ancient WeasyPrint versions with an
erstwhile Python, combine it with outdated GTK+ libraries on any Windows
version you like, but if you decide to do that **you’re on your own, don’t even
try to report an issue, kittens will die because of you.**

Step 1 - Install Python
~~~~~~~~~~~~~~~~~~~~~~~

Install the `latest Python 3.x <https://www.python.org/downloads/windows/>`_

- On Windows 32 bit download the "Windows **x86** executable installer"
- On Windows 64 bit download the "Windows **x86-64** executable installer"

Follow the `instructions <https://docs.python.org/3/using/windows.html>`_.
You may customize your installation as you like, but we suggest that you
"Add Python 3.x to PATH" for convenience and let the installer "install pip".

Step 2 - Update pip and setuptools packages
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Python is bundled with modules that may have been updated since the release.
Please open a *Command Prompt* and execute the following command:

.. code-block:: console

    python -m pip install --upgrade pip setuptools

Step 3 - Install WeasyPrint
~~~~~~~~~~~~~~~~~~~~~~~~~~~

In the console window execute the following command to install the WeasyPrint
package:

.. code-block:: console

    python -m pip install WeasyPrint

Step 4 - Install the GTK+ libraries
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

There's one thing you **must** observe:

- If your Python is 32 bit you must use the 32 bit versions of those libraries.
- If your Python is 64 bit you must use the 64 bit versions of those libraries.

If you mismatch the bitness, the warning about kittens dying applies.

In case you forgot which Python you installed, ask Python (in the console
window):

.. code-block:: console

    python --version --version

Having installed Python 64 bit you can either use the :ref:`GTK+ 64 Bit
Installer <gtk64installer>` or install the 64-bit :ref:`GTK+ via MSYS2
<msys2_gtk>`.

On Windows 32 bit or if you decided to install Python 32 bit on your Windows 64
bit machine you'll have to install the 32-bit :ref:`GTK+ via MSYS2
<msys2_gtk>`.

.. note::

    Installing those libraries doesn't mean something extraordinary. It only
    means that the files must be on your computer and WeasyPrint must be able
    to find them, which is achieved by putting the path-to-the-libs into your
    Windows ``PATH``.

.. _msys2_gtk:

Install GTK+ with the aid of MSYS2
""""""""""""""""""""""""""""""""""

Sadly the `GTK+ Runtime for 32 bit Windows
<https://gtk-win.sourceforge.io/home/index.php/Main/Home>`_ was discontinued in
April 2017.  Since then developers are advised to either bundle GTK+ with their
software (which is beyond the capacities of the WeasyPrint maintainers) or
install it through the `MSYS2 project <https://msys2.github.io/>`_.

With the help of MSYS2, both the 32 bit as well as the 64 bit GTK+ can be
installed.  If you installed the 64 bit Python and don't want to bother with
MSYS2, then go ahead and use the :ref:`GTK+ 64 Bit Installer <gtk64installer>`.

MSYS2 is a development environment. We (somehow) mis-use it to only supply the
up-to-date GTK+ runtime library files in a subfolder we can inject into our
``PATH``. But maybe you get interested in the full powers of MSYS2. It's the
perfect tool for experimenting with `MinGW
<https://en.wikipedia.org/wiki/MinGW>`_ and cross-platform development -- look
at its `wiki <https://github.com/msys2/msys2/wiki>`_.

Ok, let's install GTK3+.

* Download and run the `MSYS2 installer <http://www.msys2.org/>`_

  - On 32 bit Windows: "msys2-**i686**-xxxxxxxx.exe"
  - On 64 bit Windows: "msys2-**x86_64**-xxxxxxxx.exe"

  You alternatively may download a zipped archive, unpack it and run
  ``msys2_shell.cmd`` as described in the `MSYS2 wiki
  <https://github.com/msys2/msys2/wiki/MSYS2-installation>`_.

* Update the MSYS2 shell with

  .. code-block:: console

      pacman -Syuu

  Close the shell by clicking the close button in the upper right corner of the window.

* Restart the MSYS2 shell. Repeat the command

  .. code-block:: console

      pacman -Su

  until it says that there are no more packages to update.

* Install the GTK+ package and its dependencies.

  To install the 32 bit (**i686**) GTK run the following command:

  .. code-block:: console

      pacman -S mingw-w64-i686-gtk3

  The command for the 64 bit (**x86_64**) version is:

  .. code-block:: console

      pacman -S mingw-w64-x86_64-gtk3

  The **x86_64** package cannot be installed in the 32 bit MSYS2!

* Close the shell:

  .. code-block:: console

      exit

* Now that all the GTK files needed by WeasyPrint are in the ``.\mingw32``
  respectively in the ``.\mingw64`` subfolder of your MSYS2 installation directory,
  we can (and must) make them accessible by injecting the appropriate folder into the
  ``PATH``.

  Let's assume you installed MSYS2 in ``C:\msys2``. Then the folder to inject is:

    * ``C:\msys2\mingw32\bin`` for the 32 bit GTK+
    * ``C:\msys2\mingw64\bin`` for the 64 bit GTK+

  You can either persist it through *Advanced System Settings* -- if you don't
  know how to do that, read `How to set the path and environment variables in
  Windows <https://www.computerhope.com/issues/ch000549.htm>`_ -- or
  temporarily inject the folder before you run WeasyPrint.

.. _gtk64installer:

GTK+ 64 Bit Installer
""""""""""""""""""""""

If your Python is 64 bit you can use an installer extracted from MSYS2
and provided by Tom Schoonjans.

* Download and run the latest `gtk3-runtime-x.x.x-x-x-x-ts-win64.exe
  <https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer>`_

* If you prefer to manage your ``PATH`` environment varaiable yourself you
  should uncheck "Set up PATH environment variable to include GTK+" and supply
  it later -- either persist it through *Advanced System Settings* or
  temporarily inject it before you run WeasyPrint.

.. note::

    Checking the option doesn't insert the GTK-path at the beginning of your
    system ``PATH``, but rather **appends** it. If there is alread another
    (outdated) GTK on your ``PATH`` this will lead to unpleasant problems.

In any case: When executing WeasyPrint the GTK libraries must be on its ``PATH``.


Step 5 - Run WeasyPrint
~~~~~~~~~~~~~~~~~~~~~~~

Now that everything is in place you can test WeasyPrint.

Open a fresh *Command Prompt* and execute

.. code-block:: console

    python -m weasyprint http://weasyprint.org weasyprint.pdf

If you get an error like ``OSError: dlopen() failed to load a library: cairo /
cairo-2`` it’s probably because cairo (or another GTK+ library mentioned in the
error message) is not properly available in the folders listed in your ``PATH``
environment variable.

Since you didn't cheat and followed the instructions the up-to-date and
complete set of GTK libraries **must** be present and the error is an error.

Lets find out. Enter the following command:

.. code-block:: console

    WHERE libcairo-2.dll

This should respond with
*path\\to\\recently\\installed\\gtk\\binaries\\libcairo-2.dll*, for example:

.. code-block:: console

    C:\msys2\mingw64\bin\libcairo-2.dll

If your system answers with *nothing found* or returns a filename not related
to your recently-installed-gtk or lists more than one location and the first
file in the list isn't actually in a subfolder of your recently-installed-gtk,
then we have caught the culprit.

Depending on the GTK installation route you took, the proper folder name is
something along the lines of:

* ``C:\msys2\mingw32\bin``
* ``C:\msys2\mingw64\bin``
* ``C:\Program Files\GTK3-Runtime Win64\bin``

Determine the correct folder and execute the following commands, replace
``<path-to-recently-installed-gtk>`` accordingly:

.. code-block:: console

    SET PROPER_GTK_FOLDER=<path-to-recently-installed-gtk>
    SET PATH=%PROPER_GTK_FOLDER%;%PATH%

This puts the appropriate GTK at the beginning of your ``PATH`` and
it's files are the first found when WeasyPrint requires them.

Call WeasyPrint again:

.. code-block:: console

    python -m weasyprint http://weasyprint.org weasyprint.pdf

If the error is gone you should either fix your ``PATH`` permanently (via
*Advanced System Settings*) or execute the above ``SET PATH`` command by
default (once!) before you start using WeasyPrint.

If the error still occurs and if you really didn't cheat then you are allowed
to open a `new issue <https://github.com/Kozea/WeasyPrint/issues/new>`_. You
can also find extra help in this `bug report
<https://github.com/Kozea/WeasyPrint/issues/589>`_. If you cheated, then, you
know: Kittens already died.
