"""Test how SVG markers are drawn."""

from ...testing_utils import assert_no_logs


@assert_no_logs
def test_markers(assert_pixels):
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
          <marker id="rectangle">
            <rect x="-1" y="-1" width="3" height="3" fill="red" />
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
          <marker id="rectangle"
                  refX="1" refY="1" markerWidth="3" markerHeight="3">
            <rect width="6" height="6" fill="red" />
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
