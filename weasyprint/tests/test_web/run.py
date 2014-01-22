#!/usr/bin/env python
# coding: utf8
"""
    weasyprint.tests.test_web.run
    -----------------------------

    A simple web application made with Flask. Allows to type HTML
    and instantly visualize the result rendered by WeasyPrint.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import os.path
from flask import Flask, request, render_template, send_file
from weasyprint import HTML

app = Flask(__name__)


INPUT = os.path.join(app.root_path, 'input.html')
PNG_OUTPUT = os.path.join(app.root_path, 'output.png')
PDF_OUTPUT = os.path.join(app.root_path, 'output.pdf')

DEFAULT_CONTENT = '''
<style>
body { margin: 1em 2em; }
h1 { text-decoration : underline; }
div { border: 10px solid; background: #ddd; }
</style>

<h1>Weasyprint testing</h1>

<div><ul><li>Hello, world!
'''


@app.route('/')
def index():
    if os.path.isfile(INPUT):
        with open(INPUT) as fd:
            content = fd.read().decode('utf-8') or DEFAULT_CONTENT
    else:
        content = DEFAULT_CONTENT
    return render_template('index.html.jinja2', content=content)


@app.route('/render.png')
def render():
    html = request.args['html']
    assert html.strip()

    if html:
        assert 'fuu' not in html
        # Save the input HTML
        with open(INPUT, 'w') as fd:
            fd.write(html.encode('utf-8'))

    html = HTML(INPUT, encoding='utf8')
    html.write_pdf(PDF_OUTPUT)
    html.write_png(PNG_OUTPUT)

    return send_file(PNG_OUTPUT, cache_timeout=0)


if __name__ == '__main__':
    app.run(port=12290, debug=True)
