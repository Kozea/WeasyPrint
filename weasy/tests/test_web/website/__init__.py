# -*- coding: utf-8 -*-
"""
Flask application creation module.

"""

import os
import kalamar.site

from flask import g, Flask
from apps import frontend
from kalamar.access_point.filesystem import FileSystem, FileSystemProperty


def make_kalamar(config):
    """ Init kalamar and access points """
    kalamar_site = kalamar.site.Site()
    prefix = os.path.dirname(os.path.abspath(__file__))
    files = FileSystem(os.path.join(prefix, 'static'),
        '(.*?)\.(.*?)',
        [("name", FileSystemProperty(unicode)),
        ("ext", FileSystemProperty(unicode))],
        content_property = "data")
    kalamar_site.register("files", files)
    return kalamar_site

def create_app():
    app = Flask(__name__)
    app.debug = True
    app.register_module(frontend.app)

    kalamar_site = make_kalamar(app.config)

    app.jinja_env.trim_blocks = True
    app.jinja_env.autoescape = True

    @app.before_request
    def constants():
        """ Global context constant injector."""
        g.kalamar = kalamar_site

    return app

