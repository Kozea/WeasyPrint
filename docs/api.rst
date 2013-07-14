API
===

API stability
-------------

Everything described here is considered “public”: this is what you can rely
on. We will try to maintain backward-compatibility, although there is no
hard promise until version 1.0.

Anything else should not be used outside of WeasyPrint itself: we reserve
the right to change it or remove it at any point. Use it at your own risk,
or have dependency to a specific WeasyPrint version in your ``setup.py``
or ``requirements.txt`` file.


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
.. autofunction:: default_url_fetcher

.. module:: weasyprint.document
.. autoclass:: Document
    :members:
.. autoclass:: DocumentMetadata
    :members:
.. autoclass:: Page()
    :members:
