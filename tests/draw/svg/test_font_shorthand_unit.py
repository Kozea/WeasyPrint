from unittest.mock import Mock

from weasyprint.svg import Node


def test_parse_simple_font_shorthand():
    mock_wrapper = Mock()
    mock_style = Mock()

    node = Node(mock_wrapper, mock_style)

    assert node._parse_simple_font_shorthand("16px Arial") == {
        "font-size": "16px",
        "font-family": "Arial",
    }

    assert node._parse_simple_font_shorthand("12pt 'Times New Roman'") == {
        "font-size": "12pt",
        "font-family": "'Times New Roman'",
    }

    assert node._parse_simple_font_shorthand("12pt 'Times New Roman', Georgia") == {
        "font-size": "12pt",
        "font-family": "'Times New Roman', Georgia",
    }

    assert node._parse_simple_font_shorthand("Verdana") == {}

    assert node._parse_simple_font_shorthand("Arial 14px") == {}

    assert node._parse_simple_font_shorthand("bold 18px Georgia") == {}

    assert node._parse_simple_font_shorthand("") == {}
    assert node._parse_simple_font_shorthand("   ") == {}

    assert node._parse_simple_font_shorthand("14.5px Verdana") == {
        "font-size": "14.5px",
        "font-family": "Verdana",
    }

    assert node._parse_simple_font_shorthand("  12px  Arial  ") == {
        "font-size": "12px",
        "font-family": "Arial",
    }


def test_parse_with_various_units():
    """Test different CSS units."""

    mock_wrapper = Mock()
    mock_style = Mock()

    node = Node(mock_wrapper, mock_style)

    test_cases = [
        ("16px Arial", {"font-size": "16px", "font-family": "Arial"}),
        ("12pt Arial", {"font-size": "12pt", "font-family": "Arial"}),
        ("1.5em Arial", {"font-size": "1.5em", "font-family": "Arial"}),
        ("100% Arial", {"font-size": "100%", "font-family": "Arial"}),
        ("14mm Arial", {"font-size": "14mm", "font-family": "Arial"}),
        ("1.2cm Arial", {"font-size": "1.2cm", "font-family": "Arial"}),
    ]

    for input_str, expected in test_cases:
        result = node._parse_simple_font_shorthand(input_str)
        assert (
            result == expected
        ), f"For '{input_str}' expected {expected}, got {result}"


if __name__ == "__main__":
    test_parse_simple_font_shorthand()
    test_parse_with_various_units()
