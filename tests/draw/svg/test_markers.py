"""Test how SVG markers are drawn."""

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_markers(assert_pixels):
    assert_pixels('''
        ___________
        ___________
        _____RRR___
        _____RRR___
        _____RRR___
        ___________
        _____RRR___
        _____RRR___
        _____RRR___
        ___________
        _____RRR___
        _____RRR___
        _____RRR___
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle">
            <rect width="3" height="3" fill="red" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')


@assert_no_logs
def test_markers_viewbox(assert_pixels):
    assert_pixels('''
        ___________
        ____RRR____
        ____RRR____
        ____RRR____
        ___________
        ____RRR____
        ____RRR____
        ____RRR____
        ___________
        ____RRR____
        ____RRR____
        ____RRR____
        ___________
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle" viewBox="-1 -1 3 3">
            <rect x="-10" y="-10" width="20" height="20" fill="red" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')


@assert_no_logs
def test_markers_size(assert_pixels):
    assert_pixels('''
        ___________
        ____BBR____
        ____BBR____
        ____RRR____
        ___________
        ____BBR____
        ____BBR____
        ____RRR____
        ___________
        ____BBR____
        ____BBR____
        ____RRR____
        ___________
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle"
                  refX="1" refY="1" markerWidth="3" markerHeight="3">
            <rect width="6" height="6" fill="red" />
            <rect width="2" height="2" fill="blue" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')


@assert_no_logs
def test_markers_viewbox_size(assert_pixels):
    assert_pixels('''
        ___________
        ____RRR____
        ____RRR____
        ____RRR____
        ___________
        ____RRR____
        ____RRR____
        ____RRR____
        ___________
        ____RRR____
        ____RRR____
        ____RRR____
        ___________
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle" viewBox="-10 -10 6 6"
                  refX="-8" refY="-8" markerWidth="3" markerHeight="3">
            <rect x="-10" y="-10" width="6" height="6" fill="red" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')


def test_markers_overflow(assert_pixels):
    assert_pixels('''
        ___________
        ____BBRR___
        ____BBRR___
        ____RRRR___
        ____RRRR___
        ____BBRR___
        ____BBRR___
        ____RRRR___
        ____RRRR___
        ____BBRR___
        ____BBRR___
        ____RRRR___
        ____RRRR___
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle" overflow="visible"
                  refX="1" refY="1" markerWidth="3" markerHeight="3">
            <rect width="4" height="4" fill="red" />
            <rect width="2" height="2" fill="blue" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')


@assert_no_logs
def test_markers_userspace(assert_pixels):
    assert_pixels('''
        ___________
        ___________
        _____R_____
        ___________
        ___________
        ___________
        _____R_____
        ___________
        ___________
        ___________
        _____R_____
        ___________
        ___________
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle" markerUnits="userSpaceOnUse">
            <rect width="1" height="1" fill="red" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          stroke-width="10"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')


@assert_no_logs
def test_markers_stroke_width(assert_pixels):
    assert_pixels('''
        ___________
        ___________
        _____RRR___
        _____RRR___
        _____RRR___
        ___________
        _____RRR___
        _____RRR___
        _____RRR___
        ___________
        _____RRR___
        _____RRR___
        _____RRR___
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle">
            <rect width="1" height="1" fill="red" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          stroke-width="3"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')


@assert_no_logs
def test_markers_viewbox_stroke_width(assert_pixels):
    assert_pixels('''
        ___________
        ____BRR____
        ____RRR____
        ____RRR____
        ___________
        ____BRR____
        ____RRR____
        ____RRR____
        ___________
        ____BRR____
        ____RRR____
        ____RRR____
        ___________
    ''', '''
      <style>
        @page { size: 11px 13px }
        svg { display: block }
      </style>
      <svg width="11px" height="13px" xmlns="http://www.w3.org/2000/svg">
        <defs>
          <marker id="rectangle" viewBox="-1 -1 3 3"
                  markerWidth="1.5" markerHeight="1.5">
            <rect x="-10" y="-10" width="20" height="20" fill="red" />
            <rect x="-1" y="-1" width="1" height="1" fill="blue" />
          </marker>
        </defs>
        <path
          d="M 5 2 v 4 v 4"
          stroke-width="2"
          marker-start="url(#rectangle)"
          marker-mid="url(#rectangle)"
          marker-end="url(#rectangle)" />
      </svg>
    ''')
