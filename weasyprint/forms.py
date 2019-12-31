"""
    weasyprint.forms
    ----------------

    Post-process the PDF files created by cairo and add forms.

    :copyright: Copyright 2011-2019 Simon Sapin and contributors, see AUTHORS.
    :license: BSD, see LICENSE for details.

"""

ACROFORM = '''
<<
    /DA (/Times 10 Tf 0 g)
    /DR <<
      /Font <<
        /Times <<
          /BaseFont /Times-Roman
          /Subtype /Type1
          /Type /Font
        >>
      >>
    >>
    /Fields [{}]
>>
'''

WF_CLASSES = {
    'text': '''
<<
    /BS <<
        /S /S
        /W 1
    >>
    /FT /Tx
    /Rect [{} {} {} {}]
    /Subtype /Widget
    /Type /Annot
    /V ()
>>
''',
    'textarea': '''
<<
    /BS <<
        /S /S
        /W 1
    >>
    /Ff 4096
    /FT /Tx
    /Rect [{} {} {} {}]
    /Subtype /Widget
    /Type /Annot
    /V ()
>>
'''
}


def field_pdf(input_type, x, y, width, height):
    return WF_CLASSES[input_type].format(x, y, x + width, y + height)


def make_acroform(field_ids):
    return ACROFORM.format(' '.join('{} 0 R'.format(x) for x in field_ids))
