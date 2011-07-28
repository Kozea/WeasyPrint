#!/usr/bin/env python
from website import create_app


if __name__ == '__main__':
    app = create_app()
    app.run(port=12290)

