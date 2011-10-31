WeasyPrint converts HTML/CSS documents to PDF
=============================================

WeasyPrint is a visual rendering engine for HTML and CSS that can export
to PDF. It aims to support web standards for printing.
WeasyPrint is free software released under the `AGPL license
<https://github.com/Kozea/WeasyPrint/blob/master/COPYING>`_.

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

    weasyprint http://www.w3.org/TR/CSS21/intro.html CSS21-intro.pdf

Current status
--------------

WeasyPrint 0.1 can fetch a remote web page from an URL, find and fetch
associated stylesheets and images, and render it all to PDF or PNG.

Floats, absolute positioning and tables are not supported yet, but WeasyPrint
can already be useful for pages with “simple” layout.
See the `features </features/>`_ page for what exactly is supported or not.

Tables (among other things) are being worked on and should be in the
next version.
