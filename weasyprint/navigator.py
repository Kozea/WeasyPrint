# coding: utf8
"""
    weasyprint.navigator
    --------------------

    A WeasyPrint-based web browser. In your web browser.

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import io
import os.path

import cairo

from weasyprint import HTML, CSS, draw
from weasyprint.backends import PNGBackend
from weasyprint.formatting_structure import boxes
from weasyprint.urls import url_is_absolute


FAVICON = os.path.join(os.path.dirname(__file__),
                       'tests', 'resources', 'icon.png')


def find_links(box, links, anchors):
    link = box.style.link
    # 'link' is inherited but redundant on text boxes
    if link and not isinstance(box, boxes.TextBox):
        type_, href = box.style.link
        if type_ == 'internal':
            href = '#' + href
        else:
            href = '/' + href
        # "Border area.  That's the area that hit-testing is done on."
        # http://lists.w3.org/Archives/Public/www-style/2012Jun/0318.html
        links.append((href,) + box.hit_area())

    anchor = box.style.anchor
    if anchor:
        anchors.append((anchor,) + box.hit_area())

    if isinstance(box, boxes.ParentBox):
        for child in box.children:
            find_links(child, links, anchors)


def get_pages(html, *stylesheets):
    document = html._get_document(PNGBackend, stylesheets)
    for page, (width, height, png_bytes) in zip(
            document.pages, document.get_png_pages()):
        links = []
        anchors = []
        find_links(page, links, anchors)
        yield dict(
            width=width, height=height,
            links=links, anchors=anchors,
            data_url='data:image/png;base64,' + (
                png_bytes.encode('base64').replace('\n', '')))


def make_app():
    # Keep here imports that are not required for the rest of WeasyPrint
    from flask import Flask, request, send_file
    from jinja2 import Template

    app = Flask(__name__)

    template = Template('''
        <!doctype html>
        <meta charset=utf-8>
        <title>WeasyPrint Navigator</title>
        <style>
            form { position: fixed; z-index: 1;
                   top: 8px; left: 16px; right: 0; }
            input { font: 24px/30px sans-serif }
            input:not([type]) { background: rgba(255, 255, 255, .9);
                                border-radius: 6px; padding: 0 3px;
                                border-width: 2px }
            input:not([type]):focus { outline: none }
            body { margin-top: 0; padding-top: 50px }
            section { box-shadow: 0 0 10px 2px #aaa;
                      margin: 25px; position: relative }
            a { position: absolute; display: block }
            a[href]:hover, a[href]:focus { outline: 1px dotted }
        </style>
        <body>
        <form onsubmit="window.location.href = '/' + this.url.value;
                        return false;">
            <input name=url style="width: 85%" value="{{ url }}" />
            <input type=submit value=Go />
        </form>
        {% for page in pages %}
            <section style="width: {{ page.width }}px;
                            height: {{ page.height }}px">
                <img src="{{ page.data_url }}">
                {% for href, pos_x, pos_y, width, height in page.links %}
                    <a style="width: {{ width }}px; height: {{ height }}px;
                              left: {{ pos_x }}px; top: {{ pos_y }}px;"
                       href="{{ href }}"></a>
                {% endfor %}
                {% for anchor, pos_x, pos_y, width, height in page.anchors %}
                    <a style="left: {{ pos_x }}px; top: {#
                                Remove 60px so that the real pos is below
                                the address bar.
                              #}{{ pos_y - 60 }}px;"
                       name="{{ anchor }}"></a>
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
        return send_file(FAVICON)

    @app.route('/')
    @app.route('/<path:url>')
    def index(url=''):
        if url:
            if request.query_string:
                url += '?' + request.query_string
            if not url_is_absolute(url):
                # Default to HTTP rather than relative filenames
                url = 'http://' + url
            html = HTML(url)
            url = html.base_url
            pages = get_pages(html, stylesheet)
        else:
            pages = []
        return template.render(**locals())

    return app

if __name__ == '__main__':
    make_app().run(debug=True)
