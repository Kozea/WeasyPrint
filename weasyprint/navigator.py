# coding: utf-8
"""
    weasyprint.navigator
    --------------------

    A WeasyPrint-based web browser. In your web browser.

    :copyright: Copyright 2011-2014 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

# Do NOT import unicode_literals here. Raw WSGI requires native strings.
from __future__ import division

import os.path
from wsgiref.simple_server import make_server

from weasyprint import CSS, HTML
from weasyprint.compat import base64_encode, iteritems, parse_qs
from weasyprint.urls import url_is_absolute

FAVICON = os.path.join(os.path.dirname(__file__),
                       'tests', 'resources', 'icon.png')

STYLESHEET = CSS(string='''
   :root { font-size: 10pt }
''')


def get_pages(html):
    document = html.render(enable_hinting=True, stylesheets=[STYLESHEET])
    for page in document.pages:
        png_bytes, width, height = document.copy([page]).write_png()
        data_url = 'data:image/png;base64,' + (
            base64_encode(png_bytes).decode('ascii').replace('\n', ''))
        yield width, height, data_url, page.links, page.anchors


def render_template(url):
    parts = ['''\
<!doctype html>
<meta charset=utf-8>
<title>WeasyPrint Navigator</title>
<style>
  form { position: fixed; z-index: 1; top: 8px; left: 16px; right: 0; }
  nav, input { font: 24px/30px sans-serif }
  input:not([type]) { background: rgba(255, 255, 255, .9); border-width: 2px;
                      border-radius: 6px; padding: 0 3px }
  input:not([type]):focus { outline: none }
  body { margin-top: 0; padding-top: 50px }
  section { box-shadow: 0 0 10px 2px #aaa; margin: 25px;
            position: relative; overflow: hidden; }
  section a { position: absolute; display: block }
  section a[href]:hover, a[href]:focus { outline: 1px dotted }
  nav { margin: 25px }
</style>
<body onload="var u=document.forms[0].url; u.value || u.focus()">
<form action="/" onsubmit="
  window.location.href = '/view/' + this.url.value; return false;">
<input name=url style="width: 80%" placeholder="Enter an URL to start"
  value="''']
    write = parts.append
    if url:
        html = HTML(url)
        url = html.base_url
        write(url)
    write('" />\n<input type=submit value=Go />\n')
    if url:
        write('<a href="/pdf/')
        write(url)
        write('">PDF</a>\n')
    write('</form>\n')
    if url:
        for width, height, data_url, links, anchors in get_pages(html):
            write('<section style="width: {0}px; height: {1}px">\n'
                  '  <img src="{2}">\n'.format(width, height, data_url))
            for link_type, target, (pos_x, pos_y, width, height) in links:
                href = ('#' + target if link_type == 'internal'
                        else '/view/' + target)
                write('  <a style="left: {0}px; top: {1}px; '
                      'width: {2}px; height: {3}px" href="{4}"></a>\n'
                      .format(pos_x, pos_y, width, height, href))
            for anchor_name, (pos_x, pos_y) in iteritems(anchors):
                # Remove 60px to pos_y so that the real pos is below
                # the address bar.
                write('  <a style="left: {0}px; top: {1}px;" name="{2}"></a>\n'
                      .format(pos_x, pos_y - 60, anchor_name))
            write('</section>\n')
    else:
        write('''
<nav>
<h2>Examples:</h2>
<ul>
  <li><a href="/view/http://www.webstandards.org/files/acid2/test.html">
      Acid2</a></li>
  <li><a href="/view/http://www.w3.org/Style/CSS/current-work">
      CSS specifications</a></li>
  <li><a href="/view/http://en.wikipedia.org/">
      English Wikipedia</a></li>
</ul>
</nav>
''')
    return ''.join(parts).encode('utf8')


def normalize_url(url, query_string=None):
    if url:
        if query_string:
            url += '?' + query_string
        if not url_is_absolute(url):
            # Default to HTTP rather than relative filenames
            url = 'http://' + url
        return url


def app(environ, start_response):
    def make_response(body, status='200 OK', headers=(),
                      content_type='text/html; charset=UTF-8'):
        start_response(status, [
            ('Content-Type', content_type),
            ('Content-Length', str(len(body))),
        ] + list(headers))
        return [body]

    path = environ['PATH_INFO']

    if path == '/favicon.ico':
        with open(FAVICON, 'rb') as fd:
            return make_response(fd.read(), content_type='image/x-icon')

    elif path.startswith('/pdf/') and len(path) > 5:  # len('/pdf/') == 5
        url = normalize_url(path[5:], environ.get('QUERY_STRING'))
        body = HTML(url=url).write_pdf(stylesheets=[STYLESHEET])
        filename = url.rstrip('/').rsplit('/', 1)[-1] or 'out'
        return make_response(
            body, content_type='application/pdf',
            headers=[('Content-Disposition',
                      'attachment; filename=%s.pdf' % filename)])

    elif path.startswith('/view/'):
        url = normalize_url(path[6:], environ.get('QUERY_STRING'))
        return make_response(render_template(url))

    elif path == '/':
        args = parse_qs(environ.get('QUERY_STRING') or '')
        url = normalize_url(args.get('url', [''])[0])
        return make_response(render_template(url))

    return make_response(b'<h1>Not Found</h1>', status='404 Not Found')


def run(port=5000):
    host = '127.0.0.1'
    server = make_server(host, port, app)
    print('Listening on http://%s:%s/ ...' % (host, port))
    server.serve_forever()


if __name__ == '__main__':
    run()
