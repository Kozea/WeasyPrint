# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011-2012 Simon Sapin and contributors.
#  See AUTHORS for more details.
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.


"""
Test harness for the W3C test suite:

http://test.csswg.org/suites/css2.1/20110323/

"""

from __future__ import division, unicode_literals

import io
import os.path

import cssutils
import lxml.html
# Don’t try to import Flask on Python 3

from weasyprint import HTML, CSS


def split(something):
    return something.split(',') if something else ''


def read_testinfo(suite_directory):
    with open(os.path.join(suite_directory, '..', 'testinfo.data')) as fd:
        lines = iter(fd)
        next(lines)  # skip labels
        for line in lines:
            test_id, references, title, flags, links, _, _, assertion = \
                 line.strip(' \n').split('\t')
            yield dict(
                test_id=test_id,
                assertion=assertion,
                title=title,
                flags=split(flags),
                links=split(links),
                references=split(references),
            )


def read_chapter(filename, tests_by_link):
    url_prefix = 'http://www.w3.org/TR/CSS21/'
    for link in lxml.html.parse(filename).xpath(
            '//th/a[starts-with(@href, "%s")]' % url_prefix):
        url = link.get('href')[len(url_prefix):]
        if url in tests_by_link:
            yield (
                link.text_content().strip(),
                link.get('href'),
                tests_by_link[url]
            )


def read_toc(suite_directory, tests_by_link):
    filename = os.path.join(suite_directory, 'toc.html')
    for link in lxml.html.parse(filename).xpath('//table//a[@href]'):
        filename = os.path.join(suite_directory, link.get('href'))
        sections = list(read_chapter(filename, tests_by_link))
        if sections:
            num = sum(len(tests) for _, _, tests in sections)
            yield (link.text_content().strip(), sections, num)


def prepare_test_data(suite_directory):
    tests = {}
    tests_by_link = {}
    for test in read_testinfo(suite_directory):
        for link in test['links']:
            tests[test['test_id']] = test
            tests_by_link.setdefault(link, []).append(test)

    return list(read_toc(suite_directory, tests_by_link)), tests


def run(suite_directory):
    from flask import (
        Flask, render_template, abort, send_from_directory, safe_join)

    chapters, tests = prepare_test_data(suite_directory)

    app = Flask(__name__)
    app.jinja_env.globals['len'] = len


    @app.route('/')
    def toc():
        return render_template('toc.html',
            chapters=enumerate(chapters, 1), total=len(tests))


    @app.route('/chapter<int:chapter_num>/')
    def chapter(chapter_num):
        try:
            title, sections, _ = chapters[chapter_num - 1]
        except IndexError:
            abort(404)
        return render_template('chapter.html',
            chapter_num=chapter_num, chapter=title,
            sections=enumerate(sections, 1))


    @app.route('/chapter<int:chapter_num>/section<int:section_num>/')
    def section(chapter_num, section_num):
        try:
            chapter, sections, _ = chapters[chapter_num - 1]
            title, url, tests = sections[section_num - 1]
        except IndexError:
            abort(404)
        return render_template('section.html', **locals())


    @app.route('/tests/<test_id>/')
    def run_test(test_id):
        if test_id not in tests:
            abort(404)

        from pygments import highlight
        from pygments.lexers import HtmlLexer
        from pygments.formatters import HtmlFormatter

        with open(safe_join(suite_directory, test_id + '.htm')) as fd:
            source = fd.read()

        formatter = HtmlFormatter()
        source = highlight(source, HtmlLexer(), formatter)
        css = formatter.get_style_defs('.highlight')
        return render_template('run_test.html',
            test=tests[test_id], source=source, css=css)


    @app.route('/test-data/<path:filename>')
    def test_data(filename):
        return send_from_directory(suite_directory, filename)


    page_size_stylesheet = CSS(string='''
        @page { margin: 0; -weasy-size: 640px }
    ''')

    @app.route('/render/<test_id>.png')
    def render(test_id):
        png = HTML(safe_join(suite_directory, test_id + '.htm')).write_png(
            stylesheets=[page_size_stylesheet])
        return png, 200, {'Content-Type': 'image/png'}


    app.run(debug=True)


if __name__ == '__main__':
    run(os.path.expanduser('~/css2.1_test_suite/20110323/html4/'))
