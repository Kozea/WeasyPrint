Documentation
=============

* `Installing </install/>`_
* **Using**
* `Hacking </hacking/>`_
* `Features </using>`_

Using WeasyPrint
~~~~~~~~~~~~~~~~

As a standalone program
-----------------------

Once you have WeasyPrint `installed </install/>`_, you should have a
``weasyprint`` executable. You can just pass it the file name or the URL
of an HTML web page and the file name of the PDF or PNG file to write to.

For example::

    weasyprint http://weasyprint.org /tmp/weasyprint-website.pdf

You may see warnings about unsupported CSS on stderr.
Run ``weasyprint --help`` to see all available options.

As a Python library
-------------------

If you’re writing Python code you can import and use WeasyPrint just like
any other Python library:

.. code-block:: python

    from weasy.document import PDFDocument

    document = PDFDocument.from_file('http://weasyprint.org/')
    document.write_to('/tmp/weasyprint-website.pdf')

Which ``Document`` class you use determines the file format for the output.
Currently only PDF and PNG (in ``weasy.PNGDocument``) are supported.
These classes are instanciated with `HTML document parsed by lxml
<http://lxml.de/lxmlhtml.html#parsing-html>`_, but there are helpers
in the form of class methods. ``from_string`` takes a byte or Unicode string
while ``from_file`` can take an URL, a file name or a file-like object.

Similarly, the ``write_to`` method can take a file name or a file-like object.
The rendering of the document is lazy, so it will not happen until you
call ``write_to`` or access other attributes of the document.

**TODO:** details for the ``Document`` API.

If you want to change something in WeasyPrint or just see how it works,
it’s time to `start hacking </hacking>`_!

Logging
-------

Some errors (syntax error in CSS, unsupported CSS property, missing image, ...)
are not fatal and will not prevent a document from being rendered.

Both cssutils and WeasyPrint use the ``logging`` module from the Python
standard library to log these errors and let you know about it.
Two *loggers* are defined. The ``CSSUTILS`` logger reports syntax errors while
the ``WEASYPRINT`` reports everything else. You can access the logger objects
like this:

.. code-block:: python

    import logging
    cssutils_logger = logging.getLogger('CSSUTILS')
    weasyprint_logger = logging.getLogger('WEASYPRINT')

See the `logging documentation`_ on how to configure them.

.. _logging documentation: http://docs.python.org/library/logging.html
