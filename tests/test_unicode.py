"""Test various unicode texts and filenames."""

from weasyprint.urls import ensure_url

from .draw import document_to_pixels, html_to_pixels
from .testing_utils import FakeHTML, assert_no_logs, resource_path


@assert_no_logs
def test_unicode(assert_pixels_equal, tmp_path):
    text = 'I løvë Unicode'
    style = '''
      @page { size: 200px 50px }
      p { color: blue }
    '''
    expected_width, expected_height, expected_lines = html_to_pixels(f'''
      <style>{style}</style>
      <p><img src="pattern.png"> {text}</p>
    ''')

    stylesheet = tmp_path / 'style.css'
    image = tmp_path / 'pattern.png'
    html = tmp_path / 'doc.html'
    stylesheet.write_text(style, 'utf-8')
    image.write_bytes(resource_path('pattern.png').read_bytes())
    html_content = f'''
      <link rel=stylesheet href="{ensure_url(str(stylesheet))}">
      <p><img src="{ensure_url(str(image))}"> {text}</p>
    '''
    html.write_text(html_content, 'utf-8')

    document = FakeHTML(html, encoding='utf-8')
    width, height, lines = document_to_pixels(document)
    assert (expected_width, expected_height) == (width, height)
    assert_pixels_equal(width, height, lines, expected_lines)
