#!/usr/bin/python3

import atheris

with atheris.instrument_imports():
    from weasyprint import HTML, CSS
    from weasyprint.css.utils import InvalidValues
    import sys


def TestOneInput(data):
    fdp = atheris.FuzzedDataProvider(data)
    try:
        html = HTML(string=fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 4000)))
        css = CSS(string=fdp.ConsumeBytes(fdp.ConsumeIntInRange(0, 4000)))
        html.write_pdf(stylesheets=[css])
    except (InvalidValues, ValueError):
        pass


atheris.Setup(sys.argv, TestOneInput)
atheris.Fuzz()
