"""PDF generation management."""

from importlib.resources import files

import pydyf
from tinycss2.color4 import D50, D65

from .. import VERSION, Attachment
from ..html import W3C_DATE_RE
from ..logger import LOGGER, PROGRESS_LOGGER
from ..matrix import Matrix
from . import debug, pdfa, pdfua
from .fonts import build_fonts_dictionary
from .stream import Stream

from .anchors import (  # isort:skip
    add_annotations, add_forms, add_links, add_outlines, resolve_links,
    write_pdf_attachment)

VARIANTS = {
    name: data for variants in (pdfa.VARIANTS, pdfua.VARIANTS, debug.VARIANTS)
    for (name, data) in variants.items()}


def _w3c_date_to_pdf(string, attr_name):
    """Tranform W3C date to PDF format."""
    if string is None:
        return None
    match = W3C_DATE_RE.match(string)
    if match is None:
        LOGGER.warning(f'Invalid {attr_name} date: {string!r}')
        return None
    groups = match.groupdict()
    pdf_date = ''
    found = groups['hour']
    for key in ('second', 'minute', 'hour', 'day', 'month', 'year'):
        if groups[key]:
            found = True
            pdf_date = groups[key] + pdf_date
        elif found:
            pdf_date = f'{(key in ("day", "month")):02d}{pdf_date}'
    if groups['hour']:
        assert groups['minute']
        if groups['tz_hour']:
            assert groups['tz_hour'].startswith(('+', '-'))
            assert groups['tz_minute']
            tz_hour = int(groups['tz_hour'])
            tz_minute = int(groups['tz_minute'])
            pdf_date += f"{tz_hour:+03d}'{tz_minute:02d}"
        else:
            pdf_date += 'Z'
    return f'D:{pdf_date}'


def _reference_resources(pdf, resources, images, fonts):
    if 'Font' in resources:
        assert resources['Font'] is None
        resources['Font'] = fonts
    _use_references(pdf, resources, images)
    pdf.add_object(resources)
    return resources.reference


def _use_references(pdf, resources, images):
    # XObjects
    for key, x_object in resources.get('XObject', {}).items():
        # Images
        if x_object is None:
            image_data = images[key]
            x_object = image_data['x_object']

            if x_object is not None:
                # Image already added to PDF
                resources['XObject'][key] = x_object.reference
                continue

            image = image_data['image']
            dpi_ratio = max(image_data['dpi_ratios'])
            x_object = image.get_x_object(image_data['interpolate'], dpi_ratio)
            image_data['x_object'] = x_object

        pdf.add_object(x_object)
        resources['XObject'][key] = x_object.reference

        # Masks
        if 'SMask' in x_object.extra:
            pdf.add_object(x_object.extra['SMask'])
            x_object.extra['SMask'] = x_object.extra['SMask'].reference

        # Resources
        if 'Resources' in x_object.extra:
            x_object.extra['Resources'] = _reference_resources(
                pdf, x_object.extra['Resources'], images, resources['Font'])

    # Patterns
    for key, pattern in resources.get('Pattern', {}).items():
        pdf.add_object(pattern)
        resources['Pattern'][key] = pattern.reference
        if 'Resources' in pattern.extra:
            pattern.extra['Resources'] = _reference_resources(
                pdf, pattern.extra['Resources'], images, resources['Font'])

    # Shadings
    for key, shading in resources.get('Shading', {}).items():
        pdf.add_object(shading)
        resources['Shading'][key] = shading.reference

    # Alpha states
    for key, alpha in resources.get('ExtGState', {}).items():
        if 'SMask' in alpha and 'G' in alpha['SMask']:
            alpha['SMask']['G'] = alpha['SMask']['G'].reference


def generate_pdf(document, target, zoom, **options):
    # 0.75 = 72 PDF point per inch / 96 CSS pixel per inch
    scale = zoom * 0.75

    PROGRESS_LOGGER.info('Step 6 - Creating PDF')

    # Set properties according to PDF variants
    mark = False
    srgb = options['srgb']
    variant = options['pdf_variant']
    if variant:
        variant_function, properties = VARIANTS[variant]
        if 'mark' in properties:
            mark = properties['mark']
        if 'srgb' in properties:
            srgb = properties['srgb']

    pdf = pydyf.PDF()
    images = {}
    color_space = pydyf.Dictionary({
        'lab-d50': pydyf.Array(('/Lab', pydyf.Dictionary({
            'WhitePoint': pydyf.Array(D50),
            'Range': pydyf.Array((-125, 125, -125, 125)),
        }))),
        'lab-d65': pydyf.Array(('/Lab', pydyf.Dictionary({
            'WhitePoint': pydyf.Array(D65),
            'Range': pydyf.Array((-125, 125, -125, 125)),
        }))),
    })
    pdf.add_object(color_space)
    resources = pydyf.Dictionary({
        'ExtGState': pydyf.Dictionary(),
        'XObject': pydyf.Dictionary(),
        'Pattern': pydyf.Dictionary(),
        'Shading': pydyf.Dictionary(),
        'ColorSpace': color_space.reference,
    })
    pdf.add_object(resources)
    pdf_names = []

    # Links and anchors
    page_links_and_anchors = list(resolve_links(document.pages))

    annot_files = {}
    pdf_pages, page_streams = [], []
    compress = not options['uncompressed_pdf']
    for page_number, (page, links_and_anchors) in enumerate(
            zip(document.pages, page_links_and_anchors)):
        # Draw from the top-left corner
        matrix = Matrix(scale, 0, 0, -scale, 0, page.height * scale)

        page_width = scale * (
            page.width + page.bleed['left'] + page.bleed['right'])
        page_height = scale * (
            page.height + page.bleed['top'] + page.bleed['bottom'])
        left = -scale * page.bleed['left']
        top = -scale * page.bleed['top']
        right = left + page_width
        bottom = top + page_height

        page_rectangle = (
            left / scale, top / scale,
            (right - left) / scale, (bottom - top) / scale)
        stream = Stream(
            document.fonts, page_rectangle, resources, images, mark, compress=compress)
        stream.transform(d=-1, f=(page.height * scale))
        pdf.add_object(stream)
        page_streams.append(stream)

        pdf_page = pydyf.Dictionary({
            'Type': '/Page',
            'Parent': pdf.pages.reference,
            'MediaBox': pydyf.Array([left, top, right, bottom]),
            'Contents': stream.reference,
            'Resources': resources.reference,
        })
        if mark:
            pdf_page['Tabs'] = '/S'
            pdf_page['StructParents'] = page_number
        pdf.add_page(pdf_page)
        pdf_pages.append(pdf_page)

        add_links(links_and_anchors, matrix, pdf, pdf_page, pdf_names, mark)
        add_annotations(
            links_and_anchors[0], matrix, document, pdf, pdf_page, annot_files,
            compress)
        add_forms(
            page.forms, matrix, pdf, pdf_page, resources, stream,
            document.font_config.font_map)
        page.paint(stream, scale)

        # Bleed
        bleed = {key: value * 0.75 for key, value in page.bleed.items()}

        trim_left = left + bleed['left']
        trim_top = top + bleed['top']
        trim_right = right - bleed['right']
        trim_bottom = bottom - bleed['bottom']

        # Arbitrarly set PDF BleedBox between CSS bleed box (MediaBox) and
        # CSS page box (TrimBox) at most 10 points from the TrimBox.
        bleed_left = trim_left - min(10, bleed['left'])
        bleed_top = trim_top - min(10, bleed['top'])
        bleed_right = trim_right + min(10, bleed['right'])
        bleed_bottom = trim_bottom + min(10, bleed['bottom'])

        pdf_page['TrimBox'] = pydyf.Array([
            trim_left, trim_top, trim_right, trim_bottom])
        pdf_page['BleedBox'] = pydyf.Array([
            bleed_left, bleed_top, bleed_right, bleed_bottom])

    # Outlines
    add_outlines(pdf, document.make_bookmark_tree(scale, transform_pages=True))

    PROGRESS_LOGGER.info('Step 7 - Adding PDF metadata')

    # PDF information
    pdf.info['Producer'] = pydyf.String(f'WeasyPrint {VERSION}')
    metadata = document.metadata
    if metadata.title:
        pdf.info['Title'] = pydyf.String(metadata.title)
    if metadata.authors:
        pdf.info['Author'] = pydyf.String(', '.join(metadata.authors))
    if metadata.description:
        pdf.info['Subject'] = pydyf.String(metadata.description)
    if metadata.keywords:
        pdf.info['Keywords'] = pydyf.String(', '.join(metadata.keywords))
    if metadata.generator:
        pdf.info['Creator'] = pydyf.String(metadata.generator)
    if metadata.created:
        pdf.info['CreationDate'] = pydyf.String(
            _w3c_date_to_pdf(metadata.created, 'created'))
    if metadata.modified:
        pdf.info['ModDate'] = pydyf.String(
            _w3c_date_to_pdf(metadata.modified, 'modified'))
    if metadata.lang:
        pdf.catalog['Lang'] = pydyf.String(metadata.lang)
    if options['custom_metadata']:
        for key, value in metadata.custom.items():
            key = ''.join(char for char in key if char.isalnum())
            key = key.encode('ascii', errors='ignore').decode()
            if key:
                pdf.info[key] = pydyf.String(value)

    # Embedded files
    attachments = metadata.attachments.copy()
    if options['attachments']:
        for attachment in options['attachments']:
            if not isinstance(attachment, Attachment):
                attachment = Attachment(
                    attachment, url_fetcher=document.url_fetcher)
            attachments.append(attachment)
    pdf_attachments = []
    for attachment in attachments:
        pdf_attachment = write_pdf_attachment(pdf, attachment, compress)
        if pdf_attachment is not None:
            pdf_attachments.append(pdf_attachment)
    if pdf_attachments:
        content = pydyf.Dictionary({'Names': pydyf.Array()})
        for i, pdf_attachment in enumerate(pdf_attachments):
            content['Names'].append(pdf_attachment['F'])
            content['Names'].append(pdf_attachment.reference)
        pdf.add_object(content)
        if 'Names' not in pdf.catalog:
            pdf.catalog['Names'] = pydyf.Dictionary()
        pdf.catalog['Names']['EmbeddedFiles'] = content.reference

    # Embedded fonts
    subset = not options['full_fonts']
    pdf_fonts = build_fonts_dictionary(
        pdf, document.fonts, compress, subset, options)
    pdf.add_object(pdf_fonts)
    if 'AcroForm' in pdf.catalog:
        # Include Dingbats for forms
        dingbats = pydyf.Dictionary({
            'Type': '/Font',
            'Subtype': '/Type1',
            'BaseFont': '/ZapfDingbats',
        })
        pdf.add_object(dingbats)
        pdf_fonts['ZaDb'] = dingbats.reference
    resources['Font'] = pdf_fonts.reference
    _use_references(pdf, resources, images)

    # Anchors
    if pdf_names:
        # Anchors are name trees that have to be sorted
        name_array = pydyf.Array()
        for anchor in sorted(pdf_names):
            name_array.append(pydyf.String(anchor[0]))
            name_array.append(anchor[1])
        dests = pydyf.Dictionary({'Names': name_array})
        if 'Names' not in pdf.catalog:
            pdf.catalog['Names'] = pydyf.Dictionary()
        pdf.catalog['Names']['Dests'] = dests

    if srgb:
        # Add ICC profile.
        profile = pydyf.Stream(
            [(files(__package__) / 'sRGB2014.icc').read_bytes()],
            pydyf.Dictionary({'N': 3, 'Alternate': '/DeviceRGB'}),
            compress=compress)
        pdf.add_object(profile)
        pdf.catalog['OutputIntents'] = pydyf.Array([
            pydyf.Dictionary({
                'Type': '/OutputIntent',
                'S': '/GTS_PDFA1',
                'OutputConditionIdentifier': pydyf.String('sRGB IEC61966-2.1'),
                'DestOutputProfile': profile.reference,
            }),
        ])

    # Apply PDF variants functions
    if variant:
        variant_function(
            pdf, metadata, document, page_streams, attachments, compress)

    return pdf
