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

The ``weasyprint`` command takes two arguments: its input and output.
The input is a filename or URL to an HTML document, or ``-`` to read
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

The public API is made of two classes: ``HTML`` and ``CSS``.


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


The ``weasyprint.HTML`` class
.............................

An ``HTML`` object represents an HTML document parsed by lxml_.

.. _lxml: http://lxml.de/

You can just create an instance with a positional argument:
``doc = HTML(something)``
The class will try to guess if the input is a filename, an absolute URL,
or a file-like object.

Alternatively, you can name the argument so that no guessing is
involved:

* ``HTML(filename=foo)`` a filename, relative to the current directory
  or absolute.
* ``HTML(url=foo)`` an absolute, fully qualified URL.
* ``HTML(file_obj=foo)`` a file-like: any object with a ``read()`` method.
* ``HTML(string=foo)`` a string of HTML source. (This argument must be named.)
* ``HTML(tree=foo)`` a parsed lxml tree. (This argument must be named.)

Specifying multiple inputs is an error: ``HTML(filename=foo, url=bar)``
will raise.

You can also pass optional named arguments:

* ``encoding``: force the source character encoding
* ``base_url``: used to resolve relative URLs (eg. in
  ``<img src="../foo.png">``).
  If not passed explicitly, try to use the input filename, URL, or
  ``name`` attribute of file objects.
* ``url_fetcher``: override the URL fetcher. (See `below <#url-fetchers>`_.)

**Note:** In some cases like ``HTML(string=foo)`` you need to pass ``base_url``
explicitly, or relative URLs will be invalid.

``HTML`` objects have three public methods:

``HTML.write_pdf(target=None, stylesheets=None)``
    Render the document with stylesheets from three *origins*:

    * The HTML5 `user agent stylesheet`_;
    * Author stylesheets embedded in the document in ``<style>`` elements or
      linked by ``<link rel=stylesheet>`` elements;
    * User stylesheets provided in the ``stylesheets`` parameter to this
      method. If provided, ``stylesheets`` must be an iterable where elements
      are ``CSS`` instances (see below) or anything that can be passed
      as an unnamed argument to ``CSS()``.

    If you use this ``stylesheet`` parameter or the ``-s`` option of the
    command-line API, keep in mind that *user* stylesheets have a lower
    priority than *author* stylesheets in the cascade_.

    ``target`` can be a filename or a file-like object (anything with a
    ``write()`` method) where the PDF output is written.
    If ``target`` is not provided, the method returns the PDF content
    as a byte string.

``HTML.write_png(target=None, stylesheets=None, resolution=96)``
    Like ``write_pdf()``, but writes a single PNG image instead of PDF.

    ``resolution`` is counted in pixels in the PNG output per CSS inch.
    Note however that CSS pixels are always 1/96 CSS inch.
    With the default resolution of 96, CSS pixels match PNG pixels.

    Pages are painted in order from top to bottom, and horizontally centered.
    The resulting image is a wide as the widest page, and as high as the
    sum of all pages. There is no decoration around pages other than
    specified in CSS.

``HTML.get_png_pages(stylesheets=None, resolution=96)``
    Render each page to a separate PNG image.

    ``stylesheets`` and ``resolution`` are the same as in ``write_png()``.

    Returns a generator of ``(width, height, png_bytes)`` tuples, one for
    each page, in order. ``width`` and ``height`` are the size of the page
    in PNG pixels, ``png_bytes`` is a byte string.


.. _user agent stylesheet: https://github.com/Kozea/WeasyPrint/blob/master/weasyprint/css/html5_ua.css
.. _cascade: http://www.w3.org/TR/CSS21/cascade.html#cascading-order


The ``weasyprint.CSS`` class
............................

A ``CSS`` object represents a CSS stylesheet parsed by tinycss.
An instance is created in the same way as ``HTML``, except that
the ``tree`` parameter is not available.

``CSS`` objects have no public attribute or method. They are only meant to
be used in the ``write_pdf`` or ``write_png`` method. (See above.)

The above warning on ``base_url`` and string input applies too: relative
URLs will be invalid if there is no base URL.


URL fetchers
............

The URL fetcher is used for resources with an ``url`` input as well as
linked images and stylesheets. It is a function (or any callable) that
takes a single parameter (the URL) and should raise any exception to
indicate failure or return a dict with the following keys:

* One of ``string`` (a byte string) or ``file_obj`` (a file-like object)
* Optionally: ``mime_type``, a MIME type extracted eg. from a *Content-Type*
  header. If not provided, the type is guessed from the file extension
  in the URL.
* Optionally: ``encoding``, a character encoding extracted eg.from a
  *charset* parameter in a *Content-Type* header
* Optionally: ``redirected_url``, the actual URL of the ressource in case
  there were eg. HTTP redirects.

URL fetchers can defer to the default fetcher:

.. code-block:: python

    from weasyprint import default_url_fetcher, HTML

    def my_fetcher(url):
        if url.startswith('graph:')
            graph_data = map(float, url[6:].split(','))
            return dict(string=generate_graph(graph_data),
                        mime_type='image/png')
        else:
            return weasyprint.default_url_fetcher(url)

    source = '<img src="graph:42,10.3,87">'
    HTML(string=source, url_fetcher=my_fetcher).write_pdf('out.pdf')


Errors
------

If you get an exception when running ``write_pdf`` or ``write_png``
it is probably a bug in WeasyPrint (unless it is about writing to ``target``).
Please copy the full traceback and report it on our `issue tracker`_.

.. _issue tracker: http://redmine.kozea.fr/projects/weasyprint/issues


Logging
-------

Most errors (syntax error in CSS, unsupported CSS property, missing image, ...)
are not fatal and will not prevent a document from being rendered.

WeasyPrint uses the ``logging`` module from the Python standard library
to log these errors and let you know about them.

Logged messaged will go to stderr by default. You can change that by
configuring the ``weasyprint`` logger object:

.. code-block:: python

    import logging
    logger = logging.getLogger('weasyprint')
    logger.handlers = []  # Remove the default stderr handler
    logger.addHandler(logging.FileHandler('/path/to/weasyprint.log'))

See the `logging documentation <http://docs.python.org/library/logging.html>`_
for details.


What’s next
-----------

If you want to change something in WeasyPrint or just see how it works,
it’s time to `start hacking </hacking>`_!
