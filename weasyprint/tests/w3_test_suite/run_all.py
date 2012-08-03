# coding: utf8
"""
    weasyprint.tests.w3_test_suite.run_all
    --------------------------------------

    Run all tests from the W3C CSS 2.1 Test Suite.
    Do not check or save anything, just that there is no exception.

    See http://test.csswg.org/suites/css2.1/

    :copyright: Copyright 2011-2012 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals, print_function

import os.path
import multiprocessing
import logging

from weasyprint import HTML, LOGGER
from .web import prepare_test_data


LOGGER.handlers = []
LOGGER.addHandler(logging.NullHandler())


def run_simple(suite_directory):
    from flask import safe_join
    chapters, tests = prepare_test_data(suite_directory)
    tests = sorted(tests)
    for i, test_id in enumerate(tests):
        print('%s of %s  %s' % (i, len(tests), test_id))
        filename = safe_join(suite_directory, test_id + '.htm')
        if os.path.exists(filename):
            HTML(filename, encoding='utf-8').write_pdf()


def get_exception(data):
    test_id, filename = data
    try:
        HTML(filename, encoding='utf-8').write_pdf()
        return test_id, None
    except Exception as e:
        return test_id, '%s: %s' % (type(e).__name__, e)

def run(suite_directory):
    chapters, tests = prepare_test_data(suite_directory)
#    tests = list(tests)[:400]

    from flask import safe_join
    tests = sorted(
        (test_id, filename)
        for test_id, filename in (
            (test_id, safe_join(suite_directory, test_id + '.htm'))
            for test_id in tests
        )
        if os.path.exists(filename)
    )
    length = len(tests)

    errors = open('/tmp/a.txt', 'w')
    pool = multiprocessing.Pool(2)
    for i, (test_id, error) in enumerate(pool.imap_unordered(
            get_exception, tests)):
        print('%s of %s  %s' % (i, length, test_id))
        if error is not None:
            errors.write('%s\n%s\n\n' % (test_id, error))
            errors.flush()


if __name__ == '__main__':
    run(os.path.expanduser('~/css2.1_test_suite/20110323/html4/'))
