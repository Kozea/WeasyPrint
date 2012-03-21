# coding: utf8
"""
    weasyprint.tests.w3_test_suite.run
    ----------------------------------

    Run and automatically check the tests from the W3C CSS 2.1 Test Suite
    that have a reference rendering. (This is a small subset.)

    See http://test.csswg.org/suites/css2.1/

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals, print_function

import sys
import os.path
import logging
import traceback
from contextlib import closing

import pystacia

from weasyprint import HTML, CSS
from weasyprint.compat import urlopen


TEST_SUITE_VERSION = '20110323'

#BASE_URL = 'http://test.csswg.org/suites/css2.1/{}/html4/'
# Download and extract the zip file from http://test.csswg.org/suites/css2.1/
BASE_URL = 'file://' + os.path.expanduser('~/css2.1_test_suite/{}/html4/')

BASE_URL = BASE_URL.format(TEST_SUITE_VERSION)

RESULTS_DIRECTORY = os.path.join(os.path.dirname(__file__), 'test_results')

PAGE_SIZE_STYLESHEET = CSS(string='''
    @page { margin: 0; -weasy-size: 640px }
''')


def get_url(url):
    return closing(urlopen(BASE_URL + url))


def get_test_list():
    with get_url('reftest.list') as reflist:
        for line in reflist:
            line = line.decode('ascii')
            # Remove comments
            line = line.split('#', 1)[0]
            if not line.strip():
                # Comment-only line
                continue
            parts = line.split()
            comparaison = parts[0]
            if comparaison == '==':
                equal = True
            elif comparaison == '!=':
                equal = False
            else:
                raise ValueError(line)
            test = parts[1]
            references = parts[2:]
            assert references, 'No reference'
            yield equal, test, references


def make_test_suite():
    rendered = {}  # Memoize

    def render(name):
        result = rendered.get(name)
        if result is None:
            # name is sometimes "support/something.htm"
            basename = os.path.basename(name)
            png_filename = os.path.join(RESULTS_DIRECTORY, basename + '.png')
            png = HTML(BASE_URL + name).write_png(
                png_filename, stylesheets=[PAGE_SIZE_STYLESHEET])
            with closing(pystacia.read(png_filename)) as image:
                raw = image.get_raw('rgba')
            rendered[name] = raw
        return result

    for equal, test, references in get_test_list():
        # Use default parameter values to bind to the current values,
        # not to the variables as a closure would do.
        def test_function(equal=equal, test=test, references=references):
            test_render = render(test)
            references_render = map(render, references)
            return all((test_render != ref_render) ^ equal
                       for ref_render in references_render)
        yield test, test_function


def main():
    if not os.path.isdir(RESULTS_DIRECTORY):
        os.makedirs(RESULTS_DIRECTORY)

    logger = logging.getLogger('weasyprint')
    del logger.handlers[:]
    logger.addHandler(logging.NullHandler())

    tests = list(make_test_suite())
    passed = 0
    failed = 0
    errors = 0
    try:
        for i, (name, test) in enumerate(tests, 1):
            print('Test %i of %i: %s ' % (i, len(tests), name), end='')
            sys.stdout.flush()
            try:
                test_passed = test()
            except Exception:
                print('ERROR:')
                traceback.print_exc()
                errors += 1
            else:
                if test_passed:
                    print('PASS')
                    passed += 1
                else:
                    print('FAIL')
                    failed += 1
    except KeyboardInterrupt:
        pass
    print
    print('Passed: %i, failed: %i, errors: %i' % (passed, failed, errors))

if __name__ == '__main__':
    main()
