import os.path

from flask import Flask, render_template, jsonify


app = Flask(__name__)


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/sample.json')
def sample_json():
    # Import late so that the HTTP server starts listening quickly.
    from weasy.document import PDFDocument
    from .serialize import serialize

    sample = os.path.join(app.root_path, 'sample', 'sample.html')
    document = PDFDocument.from_file(sample)
    return jsonify(serialize(document))
