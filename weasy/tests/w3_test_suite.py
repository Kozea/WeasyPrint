# coding: utf8

#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
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


import sys
import os.path
import urllib
import logging
import traceback
from contextlib import closing

import png

from weasy.document import PNGDocument
from weasy.tests.test_draw import assert_pixels_equal


TEST_SUITE_VERSION = '20110323'

BASE_URL = 'http://test.csswg.org/suites/css2.1/{}/html4/'.format(
    TEST_SUITE_VERSION)

RESULTS_DIRECTORY = os.path.join(os.path.dirname(__file__),
                                 'test_results', 'w3')


def get_url(url):
    return closing(urllib.urlopen(BASE_URL + url))


def get_test_list():
    with get_url('reftest.list') as reflist:
        for line in reflist:
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
    rendered = set()

    def render(name):
        filename = os.path.join(RESULTS_DIRECTORY, name + '.png')
        if name not in rendered:
            PNGDocument.from_file(BASE_URL + name).write_to(filename)
            rendered.add(name)
        return filename

    def make_test(equal, test, references):
        def test_function():
            test_filename = render(test)

            reader = png.Reader(filename=test_filename)
            test_width, test_height, test_lines, test_meta = reader.read()
            test_lines = list(test_lines)

            for reference in references:
                ref_filename = render(reference)

                reader = png.Reader(filename=ref_filename)
                ref_width, ref_height, ref_lines, ref_meta = reader.read()
                ref_lines = list(ref_lines)

                if equal:
                    assert test_width == ref_width
                    assert test_height == ref_height
                    assert_pixels_equal(test, test_width, test_height,
                                        test_lines, ref_lines)
                else:
                    assert test_lines != ref_lines

        return test_function

    for equal, test, references in get_test_list():
        yield test, make_test(equal, test, references)


def main():
    if not os.path.isdir(RESULTS_DIRECTORY):
        os.makedirs(RESULTS_DIRECTORY)

    cssutils_logger = logging.getLogger('CSSUTILS')
    del cssutils_logger.handlers[:]
    cssutils_logger.addHandler(logging.NullHandler())

    logger = logging.getLogger('WEASYPRINT')
    del logger.handlers[:]
    logger.addHandler(logging.NullHandler())

    tests = list(make_test_suite())
    passed = 0
    failed = 0
    errors = 0
    try:
        for i, (name, test) in enumerate(tests, 1):
            print '### Test %i of %i: %s' % (i, len(tests), name),
            sys.stdout.flush()
            try:
                test()
            except AssertionError:
                print 'FAIL'
                failed += 1
            except Exception:
                print 'ERROR:'
                traceback.print_exc()
                errors += 1
            else:
                print 'PASS'
                passed += 1
    except KeyboardInterrupt:
        print
        print 'Passed: %i, failed: %i, errors: %i' % (passed, failed, errors)

if __name__ == '__main__':
    main()
