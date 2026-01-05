from ...testing_utils import assert_no_logs


@assert_no_logs
def test_text_fill(assert_pixels):
    assert_pixels(
        """
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    """,
        """
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <text x="0" y="1.5" style="font: 2px weasyprint" fill="blue">
          ABC DEF
        </text>
      </svg>
    """,
    )


@assert_no_logs
def test_font_shorthand_on_element_without_parent(assert_pixels):
    assert_pixels(
        """
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    """,
        """
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g>
            <text x="0" y="1.5" style="font: 2px weasyprint" fill="blue">
            ABC DEF
            </text>
        </g>
      </svg>
    """,
    )


@assert_no_logs
def test_font_shorthand_inheritance_from_parent(assert_pixels):
    assert_pixels(
        """
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    """,
        """
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g style="font: 2px weasyprint">
            <text x="0" y="1.5" fill="blue">
            ABC DEF
            </text>
        </g>
      </svg>
    """,
    )


@assert_no_logs
def test_explicit_properties_override_parent_shorthand(assert_pixels):
    assert_pixels(
        """
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    """,
        """
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g style="font: 28px Times New Roman">
            <text x="0" y="1.5" font-size="2px" font-family="weasyprint" fill="blue">
            ABC DEF
            </text>
        </g>
      </svg>
    """,
    )


@assert_no_logs
def test_font_shorthand_overrides_explicit_parent_properties(assert_pixels):
    assert_pixels(
        """
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    """,
        """
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font-size="18px" font-family="weasyprint">
            <text x="0" y="1.5" style="font: 2px weasyprint" fill="blue">
            ABC DEF
            </text>
        </g>
      </svg>
    """,
    )


@assert_no_logs
def test_child_font_shorthand_overrides_parent_shorthand(assert_pixels):
    assert_pixels(
        """
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    """,
        """
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g style="font: 34px Arial">
            <text x="0" y="1.5" style="font: 2px weasyprint" fill="blue">
            ABC DEF
            </text>
        </g>
      </svg>
    """,
    )


@assert_no_logs
def test_mixed_explicit_and_shorthand_across_levels(assert_pixels):
    assert_pixels(
        """
        BBBBBB__BBBBBB______
        BBBBBB__BBBBBB______
    """,
        """
      <style>
        @page { size: 20px 2px }
        svg { display: block }
      </style>
      <svg width="20px" height="2px" xmlns="http://www.w3.org/2000/svg">
        <g font-size="40px" font-family="Arial">
          <g style="font: 30px Georgia">
            <text x="0" y="1.5" font-size="2px" font-family="weasyprint" fill="blue">
              ABC DEF
            </text>
          </g>
        </g>
      </svg>
    """,
    )
