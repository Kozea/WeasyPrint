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

The public API for WeasyPrint 0.6 is made of two classes: ``HTML`` and ``CSS``


API stability
.............

Everything described here is considered “public”: this is what you can rely
on. We will try to maintain backward-compatibility, although there is no
hard promise until version 1.0.

Anything else should not be used outside of WeasyPrint itself: we reserve
the right to change it or remove it at any point. Please do `tell us`_
if you feel like something should be in the public API. It can probably
be added in the next version.

.. _tell us: /community/


The ``weasyprint.CSS`` class
............................

A ``CSS`` object represents a CSS stylesheet parsed by cssutils.

You can just create an instance with a positional argument:
``stylesheet = CSS(something)``
It will try to guess if the input is a filename, an absolute URL, or
a file-like object.

Alternatively, you can name the argument so that no guessing is
involved:

* ``CSS(filename=foo)`` a filename, relative to the current directory
  or absolute.
* ``CSS(url=foo)`` an absolute, fully qualified URL.
* ``CSS(file_obj=foo)`` a file-like: any object with a ``read()`` method.
* ``CSS(string=foo)`` a string of CSS source. (This argument must be named.)

Specifying multiple inputs is an error: ``CSS(filename=foo, url=bar)``
will raise.

You can also pass optional named arguments:

* ``encoding``: force the source character encoding
* ``base_url``: used to resolve relative URLs (eg. in ``@import``)
  If not passed explicitly, try to use the input filename, URL, or
  ``name`` attribute of file objects.

``CSS`` objects have no public attribute or method. They are only meant to
be used in the ``write_pdf`` or ``write_png`` method. (See below.)


The ``weasyprint.HTML`` class
.............................

An ``HTML`` object represents an HTML document parsed by lxml.
An instance is created in exactly the same way as ``CSS``.

It has two public methods:

``HTML.write_pdf(target=None, stylesheets=None)``
    Render the document with stylesheets from three *origins*:

    * The HTML5 `user agent stylesheet`_;
    * Author stylesheets embedded in the document in ``<style>`` elements or
      linked by ``<link rel=stylesheet>`` elements;
    * User stylesheets provided in the ``stylesheets`` parameter to this
      method. If provided, ``stylesheets`` must be an iterable where elements
      are ``CSS`` instances or anything that can be passed to ``CSS()``.

    ``target`` can be a filename or a file-like object (anything with a
    ``write()`` method) where the PDF output is written.
    If ``target`` is not provided, the method returns PDF as a byte string.

``HTML.write_png(target=None, stylesheets=None)``
    Like ``write_pdf``, but writes PNG instead of PDF.


.. _user agent stylesheet: https://github.com/Kozea/WeasyPrint/blob/master/weasyprint/css/html5_ua.css


Errors
------

If you get an exception when running ``write_pdf`` or ``write_png``
(unless it is about writing to ``target``), it is probably a bug
in WeasyPrint. Please copy the whole traceback and report it on our
`issue tracker`_.

.. _issue tracker: http://redmine.kozea.fr/projects/weasyprint/issues


Logging
-------

Most errors (syntax error in CSS, unsupported CSS property, missing image, ...)
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


What’s next
-----------

If you want to change something in WeasyPrint or just see how it works,
it’s time to `start hacking </hacking>`_!
