Tips & tricks
=============

This page presents some tips and tricks, mostly in the form of code snippets.

.. note::
	These tips are primarily sourced from the community. You too can share your tricks with the community, just open a PR! (If you do so, don't forget to make your code readable for the others and add some context :)).

Include header and footer of arbitrary complexity in a PDF
----------------------------------------------------------

Why this snippet?
.................

Objective: Render a header and a footer of arbitrary complexity on every page of a PDF file.

Currently, Weasyprint allow to include simple information in the margin of each page (see the report in the library `examples <https://weasyprint.org/samples/>`_). This is possible thanks to CSS3 at-rules (syntax presentation `here <https://www.quackit.com/css/at-rules/css_top-center_at-rule.cfm>`_). At-rules provide the ability to include characters in the margin of paged media. They are used to add things like page numbers or titles on the page.

Yet elements of arbitrary complexity can't be introduced in the margin. The :ref:`class <code>` in this snippet provides a solution to include any header and/or a complex footer, however complex they are.

How to use this snippet?
........................

#. Alongside the main html file that you plan to export as a PDF, create a header html and/or a footer html.
#. Render the html files as strings, as you would normally do for your main html file. Then pass these strings to the class constructor under the names ``main_html``, ``header_html`` and ``footer_html``.
#. To get your PDF simply call the method ``render_pdf``.

.. note::
	This constructor provide side margins with a sensible default of 2 centimeters. You can of course change the width of this margin if you want to. Just like you can change the default of 30 pixels between the header and footer elements and the core of the document.

How to write the header and footer?
...................................

For the HTML, the entire content of the header should be wrapped into a `header` tag and the content of the footer in a `footer` tag.

For the CSS, use fixed position and position the element yourself, either at the top for the header or the bottom for the footer.

Example CSS for a header:

.. code-block:: css

	header {
	    position: fixed;
	    top: 0;
	    left: 0;

	    height: 2.5cm;
	    width: 100%;
	    background-color: #1a1a1a;
	}

	/* For the footer, replace `top: 0` by `bottom: 0` */

The html and css of the main page don't change.

.. _code:

Show me the code!
.................

.. code-block:: python

	from weasyprint import HTML, CSS


	class PdfGenerator:
	    """
	    Generate a PDF out of a rendered template, with the possibility to integrate nicely
	    a header and a footer if provided.

	    Notes:
	    ------
	    - When Weasyprint renders an html into a PDF, it goes though several intermediate steps.
	      Here, in this class, we deal mostly with a box representation: 1 `Document` have 1 `Page`
	      or more, each `Page` 1 `Box` or more. Each box can contain other box. Hence the recursive
	      method `get_element` for example.
	      For more, see:
	      https://weasyprint.readthedocs.io/en/stable/hacking.html#dive-into-the-source
	      https://weasyprint.readthedocs.io/en/stable/hacking.html#formatting-structure
	    - Warning: the logic of this class relies heavily on the internal Weasyprint API. This
	      snippet was written at the time of the release 47, it might break in the future.
	    - This generator draws its inspiration and, also a bit of its implementation, from this
	      discussion in the library github issues: https://github.com/Kozea/WeasyPrint/issues/92
	    """
	    OVERLAY_LAYOUT = '@page {size: A4 portrait; margin: 0;}'

	    def __init__(self, main_html, header_html=None, footer_html=None,
	                 base_url=None, side_margin=2, extra_vertical_margin=30):
	        """
	        Parameters
	        ----------
	        main_html: str
	            An HTML file (most of the time a template rendered into a string) which represents
	            the core of the PDF to generate.
	        header_html: str
	            An optional header html.
	        footer_html: str
	            An optional footer html.
	        base_url: str
	            An absolute url to the page which serves as a reference to Weasyprint to fetch assets,
	            required to get our media.
	        side_margin: int, interpreted in cm, by default 2cm
	            The margin to apply on the core of the rendered PDF (i.e. main_html).
	        extra_vertical_margin: int, interpreted in pixel, by default 30 pixels
	            An extra margin to apply between the main content and header and the footer.
	            The goal is to avoid having the content of `main_html` touching the header or the
	            footer.
	        """
	        self.main_html = main_html
	        self.header_html = header_html
	        self.footer_html = footer_html
	        self.base_url = base_url
	        self.side_margin = side_margin
	        self.extra_vertical_margin = extra_vertical_margin

	    def _compute_overlay_element(self, element: str):
	        """
	        Parameters
	        ----------
	        element: str
	            Either 'header' or 'footer'

	        Returns
	        -------
	        element_body: BlockBox
	            A Weasyprint pre-rendered representation of an html element
	        element_height: float
	            The height of this element, which will be then translated in a html height
	        """
	        html = HTML(
	            string=getattr(self, f'{element}_html'),
	            base_url=self.base_url,
	        )
	        element_doc = html.render(stylesheets=[CSS(string=self.OVERLAY_LAYOUT)])
	        element_page = element_doc.pages[0]
	        element_body = PdfGenerator.get_element(element_page._page_box.all_children(), 'body')
	        element_body = element_body.copy_with_children(element_body.all_children())
	        element_html = PdfGenerator.get_element(element_page._page_box.all_children(), element)

	        if element == 'header':
	            element_height = element_html.height
	        if element == 'footer':
	            element_height = element_page.height - element_html.position_y

	        return element_body, element_height

	    def _apply_overlay_on_main(self, main_doc, header_body=None, footer_body=None):
	        """
	        Insert the header and the footer in the main document.

	        Parameters
	        ----------
	        main_doc: Document
	            The top level representation for a PDF page in Weasyprint.
	        header_body: BlockBox
	            A representation for an html element in Weasyprint.
	        footer_body: BlockBox
	            A representation for an html element in Weasyprint.
	        """
	        for page in main_doc.pages:
	            page_body = PdfGenerator.get_element(page._page_box.all_children(), 'body')

	            if header_body:
	                page_body.children += header_body.all_children()
	            if footer_body:
	                page_body.children += footer_body.all_children()

	    def render_pdf(self):
	        """
	        Returns
	        -------
	        pdf: a bytes sequence
	            The rendered PDF.
	        """
	        if self.header_html:
	            header_body, header_height = self._compute_overlay_element('header')
	        else:
	            header_body, header_height = None, 0
	        if self.footer_html:
	            footer_body, footer_height = self._compute_overlay_element('footer')
	        else:
	            footer_body, footer_height = None, 0

	        margins = '{header_size}px {side_margin} {footer_size}px {side_margin}'.format(
	            header_size=header_height + self.extra_vertical_margin,
	            footer_size=footer_height + self.extra_vertical_margin,
	            side_margin=f'{self.side_margin}cm',
	        )
	        content_print_layout = '@page {size: A4 portrait; margin: %s;}' % margins

	        html = HTML(
	            string=self.main_html,
	            base_url=self.base_url,
	        )
	        main_doc = html.render(stylesheets=[CSS(string=content_print_layout)])

	        if self.header_html or self.footer_html:
	            self._apply_overlay_on_main(main_doc, header_body, footer_body)
	        pdf = main_doc.write_pdf()

	        return pdf

	    @staticmethod
	    def get_element(boxes, element):
	        """
	        Given a set of boxes representing the elements of a PDF page in a DOM-like way, find the
	        box which is named `element`.

	        Look at the notes of the class for more details on Weasyprint insides.
	        """
	        for box in boxes:
	            if box.element_tag == element:
	                return box
	            return PdfGenerator.get_element(box.all_children(), element)


.. note::

	In the `CSS Generated Content for Paged Media Module <https://www.w3.org/TR/css-gcpm-3/>`_, the W3C proposed standards to support most expected features for print media. `Running elements <https://www.w3.org/TR/css-gcpm-3/#running-elements>`_ are the CSS compliant solution to this problem. See this `issue on the project <https://github.com/Kozea/WeasyPrint/issues/92>`_ for more details for a possible implementation.
