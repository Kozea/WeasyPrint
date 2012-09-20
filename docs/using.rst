Using WeasyPrint
================

.. _stylesheet-origins:

Stylesheet origins
------------------

HTML documents are rendered with stylesheets from three *origins*:

* The HTML5 `user agent stylesheet`_;
* Author stylesheets embedded in the document in ``<style>`` elements
  or linked by ``<link rel=stylesheet>`` elements;
* User stylesheets provided in the API.

Keep in mind that *user* stylesheets have a lower priority than *author*
stylesheets in the cascade_, unless you use `!important`_ in declarations
to raise their priority.

.. _user agent stylesheet: https://github.com/Kozea/WeasyPrint/blob/master/weasyprint/css/html5_ua.css
.. _cascade: http://www.w3.org/TR/CSS21/cascade.html#cascading-order
.. _!important: http://www.w3.org/TR/CSS21/cascade.html#important-rules


.. module:: weasyprint.__main__

As a standalone program
-----------------------

Once you have WeasyPrint :doc:`installed </install>`, you should have a
``weasyprint`` executable. Using it can be as simple as this::

    weasyprint http://weasyprint.org /tmp/weasyprint-website.pdf

You may see warnings on *stderr* about unsupported CSS.

.. autofunction:: main(argv=sys.argv)


.. module:: weasyprint

As a Python library
-------------------

If you’re writing Python code you can import and use WeasyPrint just like
any other Python library::

    import weasyprint
    weasyprint.HTML('http://weasyprint.org/').write_pdf('/tmp/weasyprint-website.pdf')

The public API is made of two classes: :class:`HTML` and :class:`CSS`.


API stability
.............

Everything described here is considered “public”: this is what you can rely
on. We will try to maintain backward-compatibility, although there is no
hard promise until version 1.0.

Anything else should not be used outside of WeasyPrint itself: we reserve
the right to change it or remove it at any point. Please do `tell us`_
if you feel like something should be in the public API. It can probably
be added in the next version.

.. _tell us: http://weasyprint.org/community/


High-level API
..............

.. autoclass:: HTML(input, **kwargs)
    :members: write_pdf, write_png, get_png_pages

.. autoclass:: CSS(input, **kwargs)


Low-level API
.............

.. versionadded:: 0.15

This low-level API gives you access to each page and their size (which may
vary within the same document!). You can then paint just a subset of the
pages, each page separately, or even use any type of cairo surface for ouput
other than PDF and PNG.


.. automethod:: HTML.render
.. autoclass:: Page
    :members:
    :member-order: bysource

.. autofunction:: pages_to_pdf

.. autofunction:: pages_to_png
.. autofunction:: pages_to_image_surface
.. autofunction:: surface_to_png


.. _url-fetchers:

URL fetchers
............

WeasyPrint goes through an *URL fetcher* to fetch external resources such as
images or CSS stylesheets. The default fetcher can natively open files
and URLs, but the HTTP client does not support advanced features like cookies
or authentication. This can be worked-around by passing a custom
``url_fetcher`` callable to the :class:`HTML` or :class:`CSS` classes.
It must have the same signature as the default fetcher:

.. autofunction:: default_url_fetcher

Custom fetchers can choose to handle some URLs and defer others
to the default fetcher:

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

Flask-WeasyPrint_ makes use of a custom URL fetcher to integrate WeasyPrint
with a Flask_ application and short-cut the network.

.. _Flask-WeasyPrint: http://packages.python.org/Flask-WeasyPrint/
.. _Flask: http://flask.pocoo.org/


Logging
.......

Most errors (syntax error in CSS, unsupported CSS property, missing image, ...)
are not fatal and will not prevent a document from being rendered.

WeasyPrint uses the ``logging`` module from the Python standard library
to log these errors and let you know about them.

Logged messaged will go to *stderr* by default. You can change that by
configuring the ``weasyprint`` logger object:

.. code-block:: python

    import logging
    logger = logging.getLogger('weasyprint')
    logger.handlers = []  # Remove the default stderr handler
    logger.addHandler(logging.FileHandler('/path/to/weasyprint.log'))

See the `logging documentation <http://docs.python.org/library/logging.html>`_
for details.


.. _navigator:

WeasyPrint Navigator
--------------------

*WeasyPrint Navigator* is a very limited web browser, running
in your web browser. Start it with:

.. code-block:: sh

    python -m weasyprint.navigator

… and open your browser at http://127.0.0.1:5000/.

It does not support cookies, forms, or many other things that you would
expect from a “real” browser. It only shows the PNG output from WeasyPrint
with overlaid clickable hyperlinks. It is mostly useful for playing and testing.


Errors
------

If you get an exception during rendering, it is probably a bug in WeasyPrint.
Please copy the full traceback and report it on our `issue tracker`_.

.. _issue tracker: https://github.com/Kozea/WeasyPrint/issues
