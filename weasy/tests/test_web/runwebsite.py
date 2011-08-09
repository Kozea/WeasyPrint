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

DEFAULT_CONTENT = """
<style>
html {
    background-color:gray;
    font-family: DejaVu Sans Mono;
    font-size:15px;
}
p {
    width:480px;
    margin:40px;
    padding: 10px;
    border-width:20px;
    vertical-align:middle;
    border-width:10px;
    border-style:solid;
}
h1 {
    text-decoration : underline;
}
</style>
<h1>Avancement de weasyprint</h1>
<p>test test </p>
"""


@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method != 'POST':
        if os.path.isfile(INPUT):
            with open(INPUT) as fd:
                content = fd.read()
        else:
            content = DEFAULT_CONTENT
        return render_template('index.html.jinja2', content=content, image=None)

    content = request.form.get("content", "").strip()

    if content:
        # Save the input HTML
        with open(INPUT, 'w') as fd:
            fd.write(content)

    pdf_document = PDFDocument.from_file(INPUT)
    pdf_document.output = PDF_OUTPUT
    pdf_document.do_layout()
    pdf_document.draw()

    png_document = PNGDocument.from_file(INPUT)
    png_document.output = PNG_OUTPUT
    png_document.do_layout()
    png_document.draw_page(0)

    with open(PNG_OUTPUT, 'rb') as fd:
        image = fd.read()

    return render_template('index.html.jinja2', content=content, image=image)


if __name__ == '__main__':
    app.run(port=12290, debug=True)

