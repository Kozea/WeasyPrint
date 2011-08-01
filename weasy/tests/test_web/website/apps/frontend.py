# -*- coding: utf-8 -*-
import os
from flask import Module, g, request, render_template
from weasy.document import PNGDocument, PDFDocument
from weasy.draw import draw_page_to_png
import StringIO

app = Module(__name__)

@app.route('/')
def index():
    content = g.kalamar.open('files',{"name":"input.html"})["data"].read()
    return render_template('index.html.jinja2', content=content, image=None)

@app.route('/', methods=("POST",))
def post():
    content = request.values.get("content", "").strip("\r\n").strip(" ")
    pdf_document = PDFDocument.from_string(content)
    pdf_document.do_layout()
    pdf_document.draw()

    png_document = PNGDocument.from_string(content)
    png_document.do_layout()
    png_document.draw_page(0)

    # save the png result
    item = g.kalamar.open('files',{"name":"png_result.png"})
    item['data'].write(png_document.output.getvalue())
    item.save()

    # save the pdf result
    item = g.kalamar.open('files',{"name":"pdf_result.pdf"})
    item['data'].write(pdf_document.output.getvalue())
    item.save()

    # Save the input HTML
    item = g.kalamar.open('files',{"name":"input.html"})
    item['data'].write(content)
    item.save()

    image = png_document.get_png_data()

    return render_template('index.html.jinja2', content=content, image=image)

