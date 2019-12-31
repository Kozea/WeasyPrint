API
===

API stability
-------------

Everything described here is considered “public”: this is what you can rely
on. We will try to maintain backward-compatibility, and we really often do, but
there is no hard promise.

Anything else should not be used outside of WeasyPrint itself. We reserve
the right to change it or remove it at any point. Use it at your own risk,
or have dependency to a specific WeasyPrint version.


Versioning
----------

Since version 43, WeasyPrint only provides major releases and does not follow
semantic versioning. This choice may look odd, but it is close to what many
browsers do, including Firefox and Chrome.

Even if each version does not break the API, each version does break the way
documents are rendered, which is what really matters at the end. Providing
minor versions would give the illusion that developers can just update
WeasyPrint without checking that everything works.

Unfortunately, we have the same problem as the other browsers: when a new
version is released, most of the user's websites are rendered exactly the same,
but a small part is not. And the only ways to know that, for web developers,
are to read the changelog and to check that their pages are correctly rendered.

More about this choice can be found in
`issue #900 <https://github.com/Kozea/WeasyPrint/issues/900>`_.


.. _command-line-api:

Command-line API
----------------

.. autofunction:: weasyprint.__main__.main(argv=sys.argv)


.. module:: weasyprint
.. _python-api:

Python API
----------

.. autoclass:: HTML(input, **kwargs)
    :members:
.. autoclass:: CSS(input, **kwargs)
.. autoclass:: Attachment(input, **kwargs)
.. autofunction:: default_url_fetcher

.. module:: weasyprint.document
.. autoclass:: Document
    :members:
.. autoclass:: DocumentMetadata()
    :members:
.. autoclass:: Page()
    :members:

.. module:: weasyprint.fonts
.. autoclass:: FontConfiguration()

.. module:: weasyprint.css.counters
.. autoclass:: CounterStyle()
