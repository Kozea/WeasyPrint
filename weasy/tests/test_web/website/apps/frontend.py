# -*- coding: utf-8 -*-
import os
from flask import Module, g, request, render_template
from weasy.document import PNGDocument
from weasy.draw import draw_page_to_png
import StringIO

app = Module(__name__)

@app.route('/')
def index():
    content = g.kalamar.open('files',{"name":"input"})["data"].read()
    return render_template('index.html.jinja2', content=content, image=None)

@app.route('/', methods=("POST",))
def post():
    content = request.values.get("content", "").strip("\r\n").strip(" ")
    document = PNGDocument.from_string(content)
    document.do_layout()
    page, = document.pages

    document.draw_page(0)
    image = document.get_png_data()

    item = g.kalamar.open('files',{"name":"input"})
    item['data'].write(content)
    item.save()

    return render_template('index.html.jinja2', content=content, image=image)

