"""Tests for logical properties."""

import pytest

from ..testing_utils import assert_no_logs


@assert_no_logs
@pytest.mark.parametrize('documents', [
    (
        '<div style="border-top: 1px solid">',
        '<div style="border-block-start: 1px solid">',
    ), (
        '<div style="border-left: 1px solid">',
        '<div style="border-inline-start: 1px solid">',
    ), (
        '<div style="border-inline-start: 1px solid">',
        '<article style="direction: rtl">'
        '  <div style="border-inline-end: 1px solid">',
    ), (
        '<div style="border-style: solid; border-width: 1px 2px">',
        '<div style="border-style: solid; border-width: logical 1px 2px">',
    ), (
        '<div style="padding-top: 1px">',
        '<div style="padding-block-start: 1px">',
    ), (
        '<div style="padding: 1px 2px 3px 4px">',
        '<div style="padding: logical 1px 4px 3px 2px">',
        '<div style="padding: 1px 2px;'
        '            padding-inline-start: 4px; padding-block-end: 3px">',
    ), (
        '<div style="margin-right: 1px">',
        '<div style="margin-inline-end: 1px">',
        '<article style="direction: rtl">'
        '  <div style="margin-inline-start: 1px">',
        '<article style="direction: rtl">'
        '  <div style="margin: logical 0 1px 0 0">',
    ), (
        '<div style="border-radius: 0 0 0 4px">',
        '<div style="border-bottom-left-radius: 4px">',
        '<div style="border-end-start-radius: 4px">',
        '<article style="direction: rtl">'
        '  <div style="border-end-end-radius: 4px">',
    ), (
        '<div style="width: 5px">',
        '<div style="inline-size: 5px">',
        '<div style="max-inline-size: 5px">',
        '<div style="max-inline-size: 5px; min-block-size: 2px">',
    ), (
        '<div style="height: 6px">',
        '<div style="block-size: 6px">',
        '<div style="min-block-size: 6px">',
        '<div style="min-block-size: 6px; max-inline-size: 10px">',
    ), (
        '<div style="position: absolute; width: 5px; inset: auto 1px auto auto">',
        '<div style="position: absolute; width: 5px; right: 1px">',
        '<div style="position: absolute; width: 5px; inset-inline-end: 1px">',
        '<div style="position: absolute; width: 5px; inset-inline: auto 1px">',
    ), (
        '<div style="float: left; width: 5px">',
        '<div style="float: inline-start; width: 5px">',
        '<article style="direction: rtl">'
        '  <div style="float: inline-end; width: 5px">',
    ), (
        '<div style="float: left; width: 5px"></div>'
        '<div style="float: left; width: 3px"></div>',
        '<div style="float: left; width: 5px"></div>'
        '<div style="float: left; width: 3px; clear: right"></div>',
        '<div style="float: inline-start; width: 5px"></div>'
        '<div style="float: left; width: 3px; clear: inline-end"></div>',
        '<div style="float: left; width: 5px"></div>'
        '<div style="float: inline-start; width: 3px; clear: inline-end"></div>',
        '<article style="direction: rtl">'
        '  <div style="float: left; width: 5px"></div>'
        '  <div style="float: inline-end; width: 3px; clear: inline-start"></div>',
    ), (
        '<div style="float: left; width: 5px"></div>'
        '<div style="float: left; width: 3px; clear: left"></div>',
        '<div style="float: inline-start; width: 5px"></div>'
        '<div style="float: left; width: 3px; clear: inline-start"></div>',
        '<div style="float: inline-start; width: 5px"></div>'
        '<div style="float: inline-start; width: 3px; clear: left"></div>',
        '<div style="float: inline-start; width: 5px"></div>'
        '<div style="float: inline-start; width: 3px; clear: both"></div>',
        '<article style="direction: rtl">'
        '  <div style="float: inline-end; width: 5px"></div>'
        '  <div style="float: inline-end; width: 3px; clear: left"></div>',
        '<article style="direction: rtl">'
        '  <div style="float: left; width: 5px"></div>'
        '  <div style="float: inline-end; width: 3px; clear: inline-end"></div>',
    ),
])
def test_logical(assert_same_renderings, documents):
    base_style = '''
    <style>
      @page { size: 10px }
      div { background: pink; background-clip: padding-box; height: 5px }
    </style>
    '''
    assert_same_renderings(*(base_style + document for document in documents))

