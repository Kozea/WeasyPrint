from weasyprint import HTML
from weasyprint.tests.testing_utils import assert_no_logs


def test_vw_vh_units():
    t = """
    <div>
    <div style="width:50vw; background-color: black; color: white">test</div>
    <div style="width:75vw; background-color: blue; color: white">test</div>
    <div style="width:100vw; background-color: blue; color: white">test</div>
    
    <div style="margin-left: 2vw">test2</div>
    
    <div style="border-radius: 10vw; margin: 5vw; background-color: lightgrey; padding: 10vw">test<br></div>
    
    <div>test this<span style="margin: 4vw">now</span></div>
    
    <table>
        <tr>
            <td style="width: 25vw">A</td>
            </td>
        </tr>
        <tr>
            <td>B</td>
            <td></td>
        </tr>
    </table>
    </div>"""

    HTML(string=t)
