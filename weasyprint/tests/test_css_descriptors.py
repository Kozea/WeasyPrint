# coding: utf-8
"""
    weasyprint.tests.test_css_descriptors
    -------------------------------------

    Test CSS descriptors.

    :copyright: Copyright 2011-2016 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

from __future__ import division, unicode_literals

import tinycss2

from ..css import preprocess_descriptors, preprocess_stylesheet
from .testing_utils import assert_no_logs, capture_logs


@assert_no_logs
def test_font_face():
    """Test the ``font-face`` rule."""
    stylesheet = tinycss2.parse_stylesheet(
        '@font-face {'
        '  font-family: Gentium Hard;'
        '  src: url(http://example.com/fonts/Gentium.woff);'
        '}')
    at_rule, = stylesheet
    assert at_rule.at_keyword == 'font-face'
    font_family, src = list(preprocess_descriptors(
        'http://weasyprint.org/foo/',
        tinycss2.parse_declaration_list(at_rule.content)))
    assert font_family == ('font_family', 'Gentium Hard')
    assert src == (
        'src', [('external', 'http://example.com/fonts/Gentium.woff')])

    stylesheet = tinycss2.parse_stylesheet(
        '@font-face {'
        '  font-family: "Fonty Smiley";'
        '  src: url(Fonty-Smiley.woff);'
        '  font-style: italic;'
        '  font-weight: 200;'
        '  font-stretch: condensed;'
        '}')
    at_rule, = stylesheet
    assert at_rule.at_keyword == 'font-face'
    font_family, src, font_style, font_weight, font_stretch = list(
        preprocess_descriptors(
            'http://weasyprint.org/foo/',
            tinycss2.parse_declaration_list(at_rule.content)))
    assert font_family == ('font_family', 'Fonty Smiley')
    assert src == (
        'src', [('external', 'http://weasyprint.org/foo/Fonty-Smiley.woff')])
    assert font_style == ('font_style', 'italic')
    assert font_weight == ('font_weight', 200)
    assert font_stretch == ('font_stretch', 'condensed')


def test_bad_font_face():
    """Test bad ``font-face`` rules."""
    stylesheet = tinycss2.parse_stylesheet(
        '@font-face {'
        '  font-family: "Bad Font";'
        '  src: url(BadFont.woff);'
        '  font-stretch: expanded;'
        '  font-style: wrong;'
        '  font-weight: bolder;'
        '  font-stretch: wrong;'
        '}')
    at_rule, = stylesheet
    assert at_rule.at_keyword == 'font-face'
    with capture_logs() as logs:
        font_family, src, font_stretch = list(
            preprocess_descriptors(
                'http://weasyprint.org/foo/',
                tinycss2.parse_declaration_list(at_rule.content)))
    assert font_family == ('font_family', 'Bad Font')
    assert src == (
        'src', [('external', 'http://weasyprint.org/foo/BadFont.woff')])
    assert font_stretch == ('font_stretch', 'expanded')
    assert logs == [
        'WARNING: Ignored `font-style: wrong` at 1:91, invalid value.',
        'WARNING: Ignored `font-weight: bolder` at 1:111, invalid value.',
        'WARNING: Ignored `font-stretch: wrong` at 1:133, invalid value.']

    stylesheet = tinycss2.parse_stylesheet('@font-face{}')
    with capture_logs() as logs:
        rules, descriptors = [], []
        preprocess_stylesheet(
            'print', 'http://wp.org/foo/', stylesheet, None, rules,
            descriptors, None)
        assert not descriptors
    assert logs == [
        "WARNING: Missing src descriptor in '@font-face' rule at 1:1"]

    stylesheet = tinycss2.parse_stylesheet('@font-face{src: url(test.woff)}')
    with capture_logs() as logs:
        rules, descriptors = [], []
        preprocess_stylesheet(
            'print', 'http://wp.org/foo/', stylesheet, None, rules,
            descriptors, None)
        assert not descriptors
    assert logs == [
        "WARNING: Missing font-family descriptor in '@font-face' rule at 1:1"]

    stylesheet = tinycss2.parse_stylesheet('@font-face{font-family: test}')
    with capture_logs() as logs:
        rules, descriptors = [], []
        preprocess_stylesheet(
            'print', 'http://wp.org/foo/', stylesheet, None, rules,
            descriptors, None)
        assert not descriptors
    assert logs == [
        "WARNING: Missing src descriptor in '@font-face' rule at 1:1"]

    stylesheet = tinycss2.parse_stylesheet(
        '@font-face { font-family: test; src: wrong }')
    with capture_logs() as logs:
        rules, descriptors = [], []
        preprocess_stylesheet(
            'print', 'http://wp.org/foo/', stylesheet, None, rules,
            descriptors, None)
        assert not descriptors
    assert logs == [
        'WARNING: Ignored `src: wrong ` at 1:33, invalid value.',
        "WARNING: Missing src descriptor in '@font-face' rule at 1:1"]

    stylesheet = tinycss2.parse_stylesheet(
        '@font-face { font-family: good, bad; src: url(test.woff) }')
    with capture_logs() as logs:
        rules, descriptors = [], []
        preprocess_stylesheet(
            'print', 'http://wp.org/foo/', stylesheet, None, rules,
            descriptors, None)
        assert not descriptors
    assert logs == [
        'WARNING: Ignored `font-family: good, bad` at 1:14, invalid value.',
        "WARNING: Missing font-family descriptor in '@font-face' rule at 1:1"]

    stylesheet = tinycss2.parse_stylesheet(
        '@font-face { font-family: good, bad; src: really bad }')
    with capture_logs() as logs:
        rules, descriptors = [], []
        preprocess_stylesheet(
            'print', 'http://wp.org/foo/', stylesheet, None, rules,
            descriptors, None)
        assert not descriptors
    assert logs == [
        'WARNING: Ignored `font-family: good, bad` at 1:14, invalid value.',
        'WARNING: Ignored `src: really bad ` at 1:38, invalid value.',
        "WARNING: Missing src descriptor in '@font-face' rule at 1:1"]
