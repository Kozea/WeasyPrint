# coding: utf8
"""
    weasyprint.browser
    ------------------

    A WeasyPrint-based web browser. In your web browser.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io

import cairo

from weasyprint import HTML, CSS, draw
from weasyprint.backends import PNGBackend
from weasyprint.formatting_structure import boxes


def find_links(box, links):
    link = box.style.link
    anchor = box.style.anchor
    if link or anchor:
        if link:
            type_, href = box.style.link
            if type_ == 'internal':
                href = '#' + href
            else:
                href = '/' + href
        else:
            href = None
        # "Border area.  That's the area that hit-testing is done on."
        # http://lists.w3.org/Archives/Public/www-style/2012Jun/0318.html
        links.append((href, anchor, box.border_box_x(), box.border_box_y(),
                      box.border_width(), box.border_height()))

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            find_links(child, links)


def surface_to_base64(surface):
    file_obj = io.BytesIO()
    surface.write_to_png(file_obj)
    return 'data:image/png;base64,' + (
        file_obj.getvalue().encode('base64').replace('\n', ''))


def get_svg_pages(html, *stylesheets):
    document = html._get_document(PNGBackend, stylesheets)
    backend = PNGBackend(None)
    result = []
    for page in document.pages:
        context = backend.start_page(page.outer_width, page.outer_height)
        draw.draw_page(document, page, context)
        width, height, surface = backend.pages.pop()
        links = []
        find_links(page, links)
        result.append(dict(
            width=width,
            height=height,
            links=links,
            data_url=surface_to_base64(surface),
        ))
    return result


def make_app():
    # Keep here imports that are not required for the rest of WeasyPrint
    from flask import Flask, request
    from jinja2 import Template

    app = Flask(__name__)

    template = Template('''
        <!doctype html>
        <meta charset=utf-8>
        <title>WeasyPrint Browser</title>
        <style>
            body { padding-top: 3em }
            form { border-bottom: 1px #888 solid; padding: .5em;
                   position: fixed; top: 0; left: 0; right: 0; z-index: 1; }
            form, input:not([type]) { background: rgba(255, 255, 255, .7) }
            input { font: 1.5em sans-serif }
            section { -webkit-box-shadow: 0 0 10px 2px #aaa;
                         -moz-box-shadow: 0 0 10px 2px #aaa;
                          -ms-box-shadow: 0 0 10px 2px #aaa;
                           -o-box-shadow: 0 0 10px 2px #aaa;
                              box-shadow: 0 0 10px 2px #aaa;
                      margin: 25px; position: relative }
            a { position: absolute; display: block }
            a[href]:hover, a[href]:focus { outline: 1px dotted }
        </style>
        <body>
        <form onsubmit="window.location.href = '/' + this.url.value;
                        return false;">
            <input name=url style="width: 90%" value="{{ url }}" />
            <input type=submit value=Go />
        </form>
        {% for page in pages %}
            <section style="width: {{ page.width }}px;
                            height: {{ page.height }}px">
                <img src="{{ page.data_url }}">
                {% for href, anchor, pos_x, pos_y, width, height
                   in page.links %}
                    <a{% if href %} href="{{ href }}"{% endif %}
                      {% if anchor %} name="{{ anchor }}"{% endif %}
                       style="width: {{ width }}px; height: {{ height }}px;
                              left: {{ pos_x }}px; top: {{ pos_y }}px;"></a>
                {% endfor %}
            </section>
        {% endfor %}
    ''')

    stylesheet = CSS(string='''
       /* @page { -weasy-size: 640px; margin: 0 }*/
       :root { font-size: 12px }
    ''')

    @app.route('/favicon.ico')
    def favicon():
        return 'No favicon yet.', 404

    @app.route('/')
    @app.route('/<path:url>')
    def index(url=''):
        if url:
            if request.query_string:
                url += '?' + request.query_string
            pages = get_svg_pages(HTML(url), stylesheet)
        else:
            pages = []
        return template.render(**locals())

    return app

if __name__ == '__main__':
    make_app().run(debug=True)
