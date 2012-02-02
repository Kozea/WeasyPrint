WeasyPrint converts HTML/CSS documents to PDF
=============================================

WeasyPrint is a visual rendering engine for HTML and CSS that can export
to PDF. It aims to support web standards for printing.
WeasyPrint is free software released under the `AGPL license
<https://github.com/Kozea/WeasyPrint/blob/master/COPYING>`_.

It is based on libraries for parsing, text and drawing but **not** on full
rendering engines like WebKit on Gecko. The CSS visual rendering is written
in Python and meant to be easy to hack on.

Get started by `installing it </install/>`_ or jump to:

 * :codelink:`Source code on GitHub`
 * `Issue tracker <http://redmine.kozea.fr/projects/weasyprint/issues>`_
 * `Continuous integration <http://jenkins.kozea.org/job/WeasyPrint/>`_
 * `Get in touch </community/>`_

Sample output
-------------

As an example, here is the `introduction chapter
<http://www.w3.org/TR/CSS21/intro.html>`_ of the CSS 2.1 spec
rendered with WeasyPrint:
`CSS21-intro.pdf </samples/CSS21-intro.pdf>`_. It was obtained by running::

    weasyprint http://www.w3.org/TR/CSS21/intro.html CSS21-intro.pdf \
        -s http://weasyprint.org/samples/CSS21-print.css

Here is the content of `CSS21-print.css`_:

.. code-block:: css

    @page {
        font-family: Palatino;
        @top-center {
            content: "Introduction to CSS 2.1";
            vertical-align: bottom;
            border-bottom: thin solid;
            margin-bottom: 1em;
        }
        @bottom-right {
            content: "Page " counter(page) " of " counter(pages);
        }
    }
    body { font-family: Palatino !important; text-align: justify; line-height: 1.25 }
    hr.navbar { display: none }
    h1 { page-break-before: auto !important }

.. _CSS21-print.css: /samples/CSS21-print.css

Current status
--------------

WeasyPrint 0.2 can fetch a remote web page from an URL, find and fetch
associated stylesheets and images, and render it all to PDF or PNG.

Floats and absolute positioning are not supported yet, but WeasyPrint
can already be useful for pages with “simple” layout (ie. static positioning
and tables.)
See the `features </features/>`_ page for what exactly is supported or not.
