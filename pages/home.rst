WeasyPrint converts HTML/CSS documents to PDF
=============================================

WeasyPrint is a free software visual rendering engine for HTML and CSS,
drawing to a cairo_ surface which can in turn export to PDF, among other formats.
It aims to support web standards for printing.

.. _cairo: http://cairographics.org/

The project is still in a very eary devlopment stage, but any `contribution
</contribute>`_ is welcome!

 * `Source code on Gitorious <https://gitorious.org/weasyprint/weasyprint>`_
 * `Issue tracker <http://redmine.kozea.fr/projects/weasyprint/issues>`_
 * Contact us by email at weasyprint@kozea.fr
 * … or on the Jabber chat-room: community@room.jabber.kozea.fr

Are you crazy?
--------------

Yes. But not that much. Each modern web browser did take many years and many
developers’ work to get where they are now, but WeasyPrint’s scope is much smaller:
there is no user-interaction, no JavaScript, no live rendering (the document
doesn’t changed after it was first parsed) and no quirks mode (we don’t need
to support every broken page of the web).

We still need however to implement the whole CSS box model and visual rendering.
This is a lot of work, but we feel we can get something useful much quicker
than `“Let’s build a rendering engine!”` may seem.
