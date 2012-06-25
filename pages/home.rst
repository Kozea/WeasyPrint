WeasyPrint converts HTML/CSS documents to PDF
=============================================

WeasyPrint is a visual rendering engine for HTML and CSS that can export
to PDF. It aims to support web standards for printing.
WeasyPrint is free software made available under the `BSD license
<https://github.com/Kozea/WeasyPrint/blob/master/LICENSE>`_.

It is based on various libraries **not**
on full a rendering engines like WebKit on Gecko. The CSS layout engine
is written in Python and meant to be easy to hack on.

Get started by `installing it </install/>`_ or jump to:

 * :codelink:`Source code` on GitHub
 * `Issue tracker <http://redmine.kozea.fr/projects/weasyprint/issues>`_
   with Redmine
 * `Continuous integration <http://jenkins.kozea.org/job/WeasyPrint/>`_
   with Jenkins
 * `Releases <http://pypi.python.org/pypi/WeasyPrint>`_ on PyPI
   (but using pip is recommended for `installing </install/>`_)
 * `Get in touch </community/>`_


Current status
--------------

Give it an URL and WeasyPrint will fetch and render a web document just
like a web browsers, except that the output is a PDF with nice page breaks.

Some important features such as floats are not supported yet,
but WeasyPrint is already used in production with complex documents.
See the `features </features/>`_ page for what exactly is supported or not.


Sample output
-------------

As an example, here is the `introduction chapter
<http://www.w3.org/TR/CSS21/intro.html>`_ of the CSS 2.1 spec
rendered with WeasyPrint:
`CSS21-intro.pdf </samples/CSS21-intro.pdf>`_. It was obtained by running::

    weasyprint http://www.w3.org/TR/CSS21/intro.html CSS21-intro.pdf -s http://weasyprint.org/samples/CSS21-print.css

Here an extract of `CSS21-print.css`_:

.. code-block:: css

    @page {
        margin: 3cm 2cm;
        padding-left: 1.5cm;
        @top-center {
            content: "Introduction to CSS 2.1";
            vertical-align: bottom;
            border-bottom: thin solid;
        }
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
        }
        @left-top {
            content: "W3C Recommendation";
            background: #005a9c; color: #fff; text-align: right;
            -weasy-transform-origin: 100% 0;
            -weasy-transform: rotate(-90deg);
        }
    }
    body { text-align: justify }
    h1 { -weasy-bookmark-level: none }

.. _CSS21-print.css: /samples/CSS21-print.css
