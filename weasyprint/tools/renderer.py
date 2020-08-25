"""
    weasyprint.tools.renderer
    -------------------------

    A simple web application allowing to type HTML and instantly visualize the
    result rendered by WeasyPrint.

"""

import argparse
from base64 import b64encode
from io import BytesIO
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from weasyprint import HTML

DEFAULT_CONTENT = '''
<style>
body { margin: 1em 2em }
h1 { text-decoration : underline }
div { border: 10px solid; background: #ddd }
</style>

<h1>Weasyprint testing</h1>

<div><ul><li>Hello, world!
'''

TEMPLATE = '''
<style>
* { box-sizing: border-box }
body { display: flex; margin: 0 }
form { display: flex; flex: 1; flex-direction: column; margin: 0 }
textarea { flex: 1; border: 1px solid; min-width: 20em }
img { border: 1px solid; max-height: 100vh; display: block }
</style>

<form method="post" action="/">
<textarea id="textarea" name="content">%s</textarea>
<input id="submit" type="submit" value="Render" accesskey="r" />
</form>
<img id="image" src="data:image/png;base64,%s" />

<script>
var timeout = null;
var textarea = document.getElementById('textarea');
var image = document.getElementById('image');
var submit = document.getElementById('submit');

textarea.oninput = function () {
  if (timeout) { clearTimeout(timeout) }
  timeout = setTimeout(function () {
    submit.disabled = true;
    var http = new XMLHttpRequest();
    http.open("POST", "/render", true);
    http.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    http.onreadystatechange = function() {
      image.src = 'data:image/png;base64,' + http.responseText;
      submit.disabled = false;
    }
    http.send('content=' + encodeURIComponent(textarea.value))
  }, 300);
}
</script>
'''


def app(environ, start_response):
    def make_response(body, status='200 OK', headers=(),
                      content_type='text/html; charset=UTF-8'):
        start_response(status, [
            ('Content-Type', content_type),
            ('Content-Length', str(len(body))),
        ] + list(headers))
        return [body]

    def get_data():
        if 'wsgi.input' in environ and request_body_size:
            request = environ['wsgi.input'].read(request_body_size)
            content = parse_qs(request.decode('utf-8'))['content'][0]
        else:
            content = DEFAULT_CONTENT
        html = HTML(string=content)
        png = BytesIO()
        html.write_png(png)
        png.seek(0)
        return content, b64encode(png.read()).decode('ascii')

    path = environ['PATH_INFO']
    request_body_size = int(environ.get('CONTENT_LENGTH') or 0)

    if path == '/':
        return make_response((TEMPLATE % get_data()).encode('utf-8'))
    elif path == '/render':
        return make_response(get_data()[1].encode('utf-8'))

    return make_response(b'<h1>Not Found</h1>', status='404 Not Found')


def run(port=5000):  # pragma: no cover
    host = '127.0.0.1'
    server = make_server(host, port, app)
    print('Listening on http://%s:%s/ ...' % (host, port))
    server.serve_forever()


if __name__ == '__main__':  # pragma: no cover
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--port', '-p', type=int, default=5000,
        help='renderer web server port')
    run(parser.parse_args().port)
