Contribute
==========

WeasyPrint is still in a very early development stage. In other words, it doesn’t
work yet.

Still, you can have a look at `the code </download>`_, report
`bugs or other issues <http://redmine.kozea.fr/projects/weasyprint>`_,
send us emails at weasyprint@kozea.fr
or just have a chat with us on the Jabber room: community@room.jabber.kozea.fr.

Even `“You’re doing it horribly wrong!”` is welcome, as long as it’s
constructive. It’s quite possible we do.

Standing on the shoulders of giants
-----------------------------------

There are many existing libraries that we can use:

 * `lxml.html <http://lxml.de/lxmlhtml.html>`_ for parsing HTML
 * `cssutils <http://code.google.com/p/cssutils/>`_ for parsing CSS
 * `lxml.cssselect <http://lxml.de/cssselect.html>`_ for CSS selectors
 * `cairo and pycairo <http://cairographics.org/pycairo/>`_ for drawing stuff
   and exporting to PDF (or other formats)
 * `Pango <http://www.pango.org/>`_ for rendering text
 * `librsvg <http://librsvg.sourceforge.net/>`_ for parsing and drawing SVG

Current status
--------------

Once HTML is parsed into DOM, much of its visual appearance can be
`expressed as CSS <http://www.w3.org/TR/CSS21/sample.html>`_ so there is not
much to do there.

The current target is to implement most of `CSS 2.1
<http://www.w3.org/TR/CSS21/cover.html>`_. WeasyPrint already `assigns
<http://www.w3.org/TR/CSS21/cascade.html>`_ a computed value for each
CSS property to every DOM element. Some details are known to be non-conformant
or just missing, but this part should already be usable. The next step is
quite big and will be the heart of WeasyPrint: design and implement a box model
and position these boxes for visual rendering, keeping page breaks in mind.

Eventually we want to support HTML5 (the parts that make sense for printing),
CSS 2.1, some CSS 3 modules (especially `Paged Media
<http://www.w3.org/TR/css3-page/>`_) and SVG.
