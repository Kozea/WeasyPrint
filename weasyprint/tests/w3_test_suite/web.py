# coding: utf8
"""
    weasyprint.tests.w3_test_suite.web
    ----------------------------------

    A simple web application to run and inspect the results of
    the W3C CSS 2.1 Test Suite.

    See http://test.csswg.org/suites/css2.1/20110323/

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import os.path

import lxml.html
# Don’t try to import Flask on Python 3

from weasyprint import HTML, CSS


def split(something):
    return something.split(',') if something else []


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


    default_stylesheet = CSS(string='''
        @page { margin: 20px; size: 680px }
        body { margin: 0 }
    ''')

    @app.route('/test/<test_id>/')
    @app.route('/chapter<int:chapter_num>/section<int:section_num>/test<int:test_index>/')
    def run_test(chapter_num=None, section_num=None, test_index=None,
                 test_id=None):
        if test_id is None:
            try:
                chapter, sections, _ = chapters[chapter_num - 1]
                title, url, tests = sections[section_num - 1]
                test = tests[test_index - 1]
                previous_index = test_index - 1
                next_index = test_index + 1 if test_index < len(tests) else None
            except IndexError:
                abort(404)
        else:
            test = dict(test_id=test_id)

        from pygments import highlight
        from pygments.lexers import HtmlLexer
        from pygments.formatters import HtmlFormatter

        filename = safe_join(suite_directory, test['test_id'] + '.htm')
        with open(filename, 'rb') as fd:
            source = fd.read().decode('utf8')

        formatter = HtmlFormatter(linenos='inline')
        source = highlight(source, HtmlLexer(), formatter)
        css = formatter.get_style_defs('.highlight')
        return render_template('run_test.html', **locals())


    @app.route('/render/<path:test_id>')
    def render(test_id):
        document = HTML(
            safe_join(suite_directory, test_id + '.htm'),
            encoding='utf8',
        ).render(stylesheets=[default_stylesheet], enable_hinting=True)
        pages = [
            'data:image/png;base64,' + document.copy([page]).write_png(
                ).encode('base64').replace('\n', '')
            for page in document.pages]
        return render_template('render.html', **locals())


    @app.route('/test-data/<path:filename>')
    def test_data(filename):
        return send_from_directory(suite_directory, filename)

    app.run(debug=True)


if __name__ == '__main__':
    run(os.path.expanduser('~/css2.1_test_suite/20110323/html4/'))
