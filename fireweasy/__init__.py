from __future__ import division, unicode_literals

import os.path


def make_app():
    from flask import Flask, render_template, jsonify


    app = Flask(__name__)


    @app.route('/')
    def home():
        return render_template('home.html')


    @app.route('/sample.json')
    def sample_json():
        # Import late so that the HTTP server starts listening quickly.
        from weasyprint import HTML
        from weasyprint.document import PDFDocument
        from .serialize import serialize

        sample = os.path.join(app.root_path, 'sample', 'sample.html')
        document = HTML(sample)._get_document(PDFDocument, [])
        return jsonify(serialize(document))

    return app
