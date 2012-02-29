Documentation
=============

* `Installing </install/>`_
* **Using**
* `Hacking </hacking/>`_
* `Features </features/>`_

Using WeasyPrint
~~~~~~~~~~~~~~~~

As a standalone program
-----------------------

Once you have WeasyPrint `installed </install/>`_, you should have a
``weasyprint`` executable. Using it can be as simple as this::

    weasyprint http://weasyprint.org /tmp/weasyprint-website.pdf

You may see warnings on stderr about unsupported CSS.

The ``weasyprint`` command takes two arguments: its input and its output.
The input is a filename or an URL to an HTML document, or ``-`` to read
HTML from stdin. The output is a filename, or ``-`` to write to stdout.

More options are available:

``-e`` or ``--encoding``
    Force the input character encoding (eg. ``-e utf8``).

``-f`` or ``--format``
    Choose the output file format among PDF and PNG (eg. ``-f png``).
    Required if the output is not a ``.pdf`` or ``.png`` filename.

``-s`` or ``--stylesheet``
    Add a user CSS stylesheet to the document. (eg. ``-s print.css``).
    Multiple stylesheets are allowed.

``--version``
    Show the version number.

``-h`` or ``--help``
    Show the command-line usage.


As a Python library
-------------------

If you’re writing Python code you can import and use WeasyPrint just like
any other Python library:

.. code-block:: python

    import weasyprint
    weasyprint.HTML('http://weasyprint.org/').write_pdf('/tmp/weasyprint-website.pdf')

**TODO**: full documentation for the public API.

If you want to change something in WeasyPrint or just see how it works,
it’s time to `start hacking </hacking>`_!

Errors
------

If you get an exception from WeasyPrint during the document layout,
*this is a bug*. Please copy the whole traceback and report it on our `issue tracker`_. (An error while loading your input document or writing the output is
probably not a bug in WeasyPrint, though.)

.. _issue tracker: http://redmine.kozea.fr/projects/weasyprint/issues

Logging
-------

Some errors (syntax error in CSS, unsupported CSS property, missing image, ...)
are not fatal and will not prevent a document from being rendered.

Both cssutils and WeasyPrint use the ``logging`` module from the Python
standard library to log these errors and let you know about it.
Two *loggers* are defined. The ``CSSUTILS`` logger reports syntax errors while
the ``weasyprint`` reports everything else. You can access the logger objects
like this:

.. code-block:: python

    import logging
    cssutils_logger = logging.getLogger('CSSUTILS')
    weasyprint_logger = logging.getLogger('weasyprint')

Logged messaged will go to stderr by default.
See the `logging documentation`_ if you want to change that.

.. _logging documentation: http://docs.python.org/library/logging.html
