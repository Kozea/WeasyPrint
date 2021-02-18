Common Use Cases
================


Include in Web Applications
---------------------------

Using WeasyPrint in web applications sometimes requires attention on some
details.

First of all, rendering untrusted HTML and CSS files can lead to :ref:`security
problems <Security>`. Please be sure to carefully follow the different proposed
solutions if you allow your users to modify the source of the rendered
documents in any way.

Another problem is rights management: you often need to render templates that
can only be accessed by authenticated users, and WeasyPrint installed on the
server doesn’t send the same cookies as the ones sent by the users. Extensions
such as Flask-WeasyPrint_ (for Flask_) or Django-WeasyPrint_ (for Django_)
solve this issue with a small amount of code. If you use another framework, you
can read these extensions and probably find an equivalent workaround.

.. _Flask-Weasyprint: https://github.com/Kozea/Flask-WeasyPrint
.. _Flask: http://flask.pocoo.org/
.. _Django-WeasyPrint: https://github.com/fdemmer/django-weasyprint
.. _Django: https://www.djangoproject.com/


Adjust Document Dimensions
--------------------------

WeasyPrint does not provide support for adjusting page size or document margins
via command-line flags. This is best accomplished with the CSS ``@page``
at-rule. Consider the following example:

.. code-block:: css

  @page {
    size: Letter; /* Change from the default size of A4 */
    margin: 3cm; /* Set margin on each page */
  }

There is much more which can be achieved with the ``@page`` at-rule,
such as page numbers, headers, etc. Read more about the page_ at-rule.

.. _page: https://developer.mozilla.org/en-US/docs/Web/CSS/@page


Improve Rendering Speed and Memory Use
--------------------------------------

WeasyPrint is often slower than other web engines. Python is the usual suspect,
but it’s not the main culprit here. :ref:`Optimization is not the main goal of
WeasyPrint <Why Python?>` and it may lead to unbearable long rendering times.

First of all: WeasyPrint’s performance gets generally better with time. You can
check WeasyPerf_ to compare time and memory needed across versions.

Some tips may help you to get better results.

- A high number of CSS properties with a high number of HTML tags can lead to a
  huge amount of time spent for the cascade. Avoiding large CSS frameworks can
  drastically reduce the rendering time.
- Tables are known to be slow, especially when they are rendered on multiple
  pages. When possible, using a common block layout instead gives much faster
  layouts.
- Encoding detection can be really slow when HTML lines are really long.
  Providing an explicit encoding or removing the ``chardet`` module fixes the
  problem (see `#29`_).

.. _WeasyPerf: https://kozea.github.io/WeasyPerf/
.. _#29: https://github.com/chardet/chardet/issues/29
