#!/usr/bin/env python

import os.path
from flask import Flask, request, render_template
from weasy.document import PNGDocument, PDFDocument
from weasy.draw import draw_page_to_png
#import StringIO

app = Flask(__name__)


INPUT = os.path.join(app.root_path, 'input.html')
PNG_OUTPUT = os.path.join(app.root_path, 'output.png')
PDF_OUTPUT = os.path.join(app.root_path, 'output.pdf')


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method != 'POST':
        with open(INPUT) as fd:
            content = fd.read()
        return render_template('index.html.jinja2', content=content, image=None)

    content = request.form.get("content", "").strip()

    # Save the input HTML
    with open(INPUT, 'w') as fd:
        fd.write(content)

    pdf_document = PDFDocument.from_string(content)
    pdf_document.output = PDF_OUTPUT
    pdf_document.do_layout()
    pdf_document.draw()

    png_document = PNGDocument.from_string(content)
    png_document.output = PNG_OUTPUT
    png_document.do_layout()
    png_document.draw_page(0)

    with open(PNG_OUTPUT, 'rb') as fd:
        image = fd.read()

    return render_template('index.html.jinja2', content=content, image=image)


if __name__ == '__main__':
    app.run(port=12290, debug=True)
