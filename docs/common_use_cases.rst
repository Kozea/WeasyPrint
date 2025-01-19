Common Use Cases
================


Include in Web Applications
---------------------------

Using WeasyPrint in web applications sometimes requires attention on some
details.

Security Problems
.................

First of all, rendering untrusted HTML and CSS files can lead to :ref:`security
problems <Security>`. Please be sure to carefully follow the different proposed
solutions if you allow your users to modify the source of the rendered
documents in any way.

Rights Management
.................

Another problem is rights management: you often need to render templates that
can only be accessed by authenticated users, and WeasyPrint installed on the
server doesn’t send the same cookies as the ones sent by the users. Extensions
such as Flask-WeasyPrint_ (for Flask_) or Django-WeasyPrint_ (for Django_)
solve this issue with a small amount of code. If you use another framework, you
can read these extensions and probably find an equivalent workaround.

.. _Flask-Weasyprint: https://github.com/Kozea/Flask-WeasyPrint
.. _Flask: https://flask.palletsprojects.com/
.. _Django-WeasyPrint: https://github.com/fdemmer/django-weasyprint
.. _Django: https://www.djangoproject.com/

Server Side Requests & Self-Signed SSL Certificates
...................................................

If your server is requesting data from itself, you may encounter a self-signed
certificate error, even if you have a valid certificate.

You need to add yourself as a Certificate Authority, so that your self-signed
SSL certificates can be requested.

.. code-block:: bash

   # If you have not yet created a certificate.
   sudo openssl req -x509 \
       -sha256 \
       -nodes \
       -newkey rsa:4096 \
       -days 365 \
       -keyout localhost.key \
       -out localhost.crt

   # Follow the prompts about your certificate and the domain name.
   openssl x509 -text -noout -in localhost.crt

Add your new self-signed SSL certificate to your nginx.conf, below the line
``server_name 123.123.123.123;``:

.. code-block:: bash

   ssl_certificate /etc/ssl/certs/localhost.crt;
   ssl_certificate_key /etc/ssl/private/localhost.key;

The SSL certificate will be valid when accessing your website from the
internet. However, images will not render when requesting files from the same
server.

You will need to add your new self-signed certificates as trusted:

.. code-block:: bash

   sudo cp /etc/ssl/certs/localhost.crt /usr/local/share/ca-certificates/localhost.crt
   sudo cp /etc/ssl/private/localhost.key /usr/local/share/ca-certificates/localhost.key

   # Update the certificate authority trusted certificates.
   sudo update-ca-certificates

   # Export your newly updated Certificate Authority Bundle file.
   # If using Django, it will use the newly signed certificate authority as
   # valid and images will load properly.
   sudo tee -a /etc/environment <<< 'export REQUESTS_CA_BUNDLE=/etc/ssl/certs/ca-certificates.crt'


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


Generate PDFs Specialized for Accessibility (PDF/UA) and Archiving (PDF/A)
--------------------------------------------------------------------------

WeasyPrint can generate different PDF variants, including PDF/UA and PDF/A. The
feature is available by using the ``--pdf-variant`` CLI option, or the
``pdf_variant`` Python parameter of :func:`HTML.write_pdf
<weasyprint.HTML.write_pdf>`.

.. code-block:: python

  from weasyprint import HTML
  HTML(string="<p>document</p>").write_pdf("document.pdf", pdf_variant="pdf/a-3u")

.. code-block:: sh

  $ weasyprint document.html --pdf-variant="pdf/ua-1" document.pdf

The different supported variants can be listed using ``weasyprint --help``.

Even if WeasyPrint tries to generate valid documents, the result is not
guaranteed: the HTML, CSS and PDF features chosen by the user must follow the
limitations defined by the different specifications.

PDF/A
.....

PDF/A documents are specialized for archiving purposes. They are a simple
subset of PDF, with a lot of limitations: no audio, video or JavaScript,
defined color spaces, embedded fonts, etc.

If possible, PDF/A-3u should be preferred: it allows transparency layers that
are forbidden in A-1, and arbitrary formats for attached files that are
forbidden in A-2. The "u" part of the variant indicates that the PDF text is
available as Unicode.

PDF/A documents include a PDF identifier, that is mainly useful to indicate
that a PDF is a new version of another PDF. By default, WeasyPrint generates a
valid PDF identifier, but you can provide your own with the
``--pdf-identifier`` CLI option or ``pdf_identifier`` Python parameter.

If your document includes images, you must set the ``image-rendering:
crisp-edges`` property to avoid anti-aliasing, that is forbidden by PDF/A.

PDF/UA
......

PDF/UA documents are specialized for accessibility purposes. They include extra
metadata that define document information and content structure.

The main constraint to get valid PDF/UA documents is to use a correct HTML
structure, to avoid inconsistencies in the PDF structure. The HTML order is
also used to define the order of the PDF content.

Some information is required in your HTML file, including a ``<title>`` tag,
and a ``lang`` attribute set on the ``<html>`` tag.


Include PDF Forms
-----------------

By default, form fields are transformed into pure text and graphical shapes
when exported to PDF. But WeasyPrint gives the possibility to generate real PDF
forms that can be filled with a PDF reader. These forms can even send requests
with the data filled in the PDF, just as the same form would do in a web
browser.

To transform all HTML forms into PDF forms, you can use the ``--pdf-forms`` CLI
option or ``pdf_forms`` Python parameter.

.. code-block:: python

  from weasyprint import HTML
  HTML(string="<input value='test'>").write_pdf("test.pdf", pdf_forms=True)

.. code-block:: sh

  $ weasyprint document.html --pdf-forms document.pdf

You can also define which specific fields (``input``, ``select``, ``textarea``,
``button``) have to be transformed into PDF forms by setting the ``appearance``
CSS property to ``auto`` on them. In this case, as for browsers, you’ll have to
manually override the default style set by the user agent stylesheet. Reading
`the stylesheet set by the --pdf-forms option
<https://github.com/Kozea/WeasyPrint/blob/main/weasyprint/css/html5_ua_form.css>`_
can help to override this style.

.. code-block:: html

  <style>
    label { display: block }
    .pdf-form { appearance: auto }
    .pdf-form::before { visibility: hidden }
  </style>
  <label>
    Can't be modified in PDF
    <input value="static">
  </label>
  <label>
    Can be modified in PDF
    <input class="pdf-form" value="dynamic">
  </label>

PDF forms support can be quite poor depending on the PDF reader you use. If a
feature doesn’t work for you, please check that this feature is actually
supported by your PDF reader before reporting a bug.


Define PDF Metadata
-------------------

PDF documents can include various metadata, such as title, authors or creation
date. The easiest way to define them is to include them in your HTML file:
these fields are normalized and can be automatically picked up by WeasyPrint.

.. code-block:: html

  <html lang="en">
    <head>
      <title>PDF Sample with Metadata</title>
      <meta name="author" content="Jane Doe">
      <meta name="author" content="John Doe">
      <meta name="generator" content="HTML generator">
      <meta name="keywords" content="HTML, CSS, PDF">
      <meta name="dcterms.created" content="2000-12-31T12:34:56+02:00">
      <meta name="dcterms.modified" content="2010-07-14">
      <meta name="description" content="This is a simple sample">
    </head>
  </html>

HTML metadata values listed here, including language and title, are stored in
the corresponding, normalized fields in PDF.

If you use custom metadata fields, they are not stored in PDF by default. You
can include them in the PDF info dictionary using the ``--custom-metadata`` CLI
option or the ``custsom_metadata`` Python parameter.

.. code-block:: python

  from weasyprint import HTML
  HTML(string="<meta name="recipe" content="fries">").write_pdf("recipe.pdf", custom_metadata=True)

.. code-block:: sh

  $ weasyprint document.html --custom-metadata document.pdf


Attach Files
------------

You can attach files to your generated PDF. These files can be opened when a
link is clicked in the PDF, or just available in the list of attached files in
your PDF reader.

To attach a file with a regular link, you can use a regular anchor with the
``rel`` attribute set to ``attachment``.

.. code-block:: html

  <a rel="attachment" href="note.txt">view attached note</a>

To attach a file globally to the document, you can add a ``link`` tag in your
``head``:

.. code-block:: html

  <link rel="attachment" href="note.txt">

If you don’t want to attach your files using HTML tags, you can also use the
``--attachment`` CLI option, multiple times if needed.

.. code-block:: sh

  $ weasyprint document.html --attachment note.txt --attachment photo.jpg document.pdf

In a Python script, you can also attach files using the
:class:`weasyprint.Attachment` class.

.. code-block:: python

  from weasyprint import Attachment, HTML
  attachments = [Attachment("note.txt"), Attachment("photo.jpg")]
  HTML(string="<p>PDF with attachments</p>").write_pdf("recipe.pdf", attachments=attachments)


Cache and Optimize Images
-------------------------

WeasyPrint provides many options to deal with images: ``optimize_images``,
``jpeg_quality``, ``dpi`` and ``cache``.

``optimize_images`` can enable size optimization for images. When enabled, the
generated PDF will include smaller images with no quality penalty, but the
rendering time may be slightly increased.

The ``jpeg_quality`` option can be set to decrease the quality of JPEG images
included in the PDF. You can set a value between 95 (best quality) to 0
(smaller image size), depending on your needs.

The ``dpi`` option offers the possibility to reduce the size (in pixels, and
thus in bytes) of all included raster images. The resolution, set in dots per
inch, indicates the maximum number of pixels included in one inch on the
generated PDF.

.. code-block:: python

    # Original high-quality images, faster, but generated PDF is larger
    HTML('https://weasyprint.org/').write_pdf('weasyprint.pdf')

    # Optimized lower-quality images, a bit slower, but generated PDF is smaller
    HTML('https://weasyprint.org/').write_pdf(
        'weasyprint.pdf', optimize_images=True, jpeg_quality=60, dpi=150)

``cache`` gives the possibility to use a cache for images, avoiding to
download, parse and optimize them each time they are used.

By default, the cache is used document by document, but you can share it
between documents if needed. This feature can save a lot of network and CPU
time when you render a lot of documents that use the same images.

.. code-block:: python

    cache = {}
    for i in range(10):
        HTML(f'https://weasyprint.org/').write_pdf(
            f'example-{i}.pdf', cache=cache)

It’s also possible to cache images on disk instead of keeping them in memory.
The ``--cache-folder`` CLI option can be used to define the folder used to
store temporary images. You can also provide this folder path as a string for
``cache``.


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
  renderings.
- Optimizing images and fonts can reduce the PDF size, but increase the
  rendering time. Moreover, caching images gives the possibility to read and
  optimize images only once, and thus to save time when the same image is used
  multiple times. See :ref:`Cache and Optimize Images`.

.. _WeasyPerf: https://kozea.github.io/WeasyPerf/


Show Log Messages
-----------------

Most errors (unsupported CSS property, missing image…) are not fatal and will
not prevent a document from being rendered. WeasyPrint uses the :mod:`logging`
module from the Python standard library to log these errors and let you know
about them.

When WeasyPrint is launched in a terminal, logged messages will go to the
standard error stream (``stderr``) by default. When used as a library, logs are
not displayed at all. You can change that by configuring the ``weasyprint``
logger object:

.. code-block:: python

    import logging
    logger = logging.getLogger('weasyprint')

    # Display warnings, errors and critical messages.
    logger.setLevel(logging.WARNING)

    # Save logs to the weasyprint.log file.
    logger.addHandler(logging.FileHandler('weasyprint.log'))
    # Print logs on console.
    logger.addHandler(logging.StreamHandler())

The ``weasyprint.progress`` logger is used to report the rendering progress. It
is useful to get feedback when WeasyPrint is launched in a terminal (using the
``--verbose`` or ``--debug`` option), or to give this feedback to end users
when used as a library.

See the documentation of the :mod:`logging` module for details.
