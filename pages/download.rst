Download
========

WeasyPrint is not packaged yet, but you can find the source code `on Gitorious
<https://gitorious.org/weasyprint/weasyprint>`_::

    git clone git://gitorious.org/weasyprint/weasyprint.git

WeasyPrint requires `changes <https://github.com/SimonSapin/cssutils>`_ to
cssutils that are not integrated `upstream
<http://code.google.com/p/cssutils/>`_ yet::

    git clone git://github.com/SimonSapin/cssutils.git

To install it all in a `virtualenv <http://www.virtualenv.org/>`_:

.. code-block:: sh

    . /path/to/my_venv/bin/activate
    cd /path/to/cssutils
    pip install -e .
    cd /path/to/weasyprint
    pip install -e .

pip will automatically install dependencies. You may need to install Python
development headers to compile the C extension for lxml.
