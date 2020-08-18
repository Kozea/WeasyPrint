from weasyprint import HTML
from weasyprint.tests.testing_utils import assert_no_logs


def test_rem_units():
    t = """
    <div>
    <div style="width:50vw; background-color: black; color: white">test</div>
    <div style="width:75vw; background-color: blue; color: white">test</div>
    </div>"""

    HTML(string=t).write_pdf('test.pdf')
