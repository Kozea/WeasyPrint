"""PDF stream."""

import hashlib
import io
import struct

import pydyf
from fontTools import subset
from fontTools.ttLib import TTFont, TTLibError, ttFont

from ..logger import LOGGER
from ..matrix import Matrix
from ..text.ffi import ffi, harfbuzz, pango


class Font:
    def __init__(self, pango_font, hb_face):
        hb_blob = ffi.gc(
            harfbuzz.hb_face_reference_blob(hb_face),
            harfbuzz.hb_blob_destroy)
        with ffi.new('unsigned int *') as length:
            hb_data = harfbuzz.hb_blob_get_data(hb_blob, length)
            self.file_content = ffi.unpack(hb_data, int(length[0]))
        self.index = harfbuzz.hb_face_get_index(hb_face)

        pango_metrics = pango.pango_font_get_metrics(pango_font, ffi.NULL)
        description = pango.pango_font_describe(pango_font)
        font_size = pango.pango_font_description_get_size(description)
        self.style = pango.pango_font_description_get_style(description)
        self.family = ffi.string(
            pango.pango_font_description_get_family(description))
        digest = hashlib.sha1(self.file_content + bytes(self.index)).digest()
        self.hash = ''.join(chr(65 + letter % 26) for letter in digest[:6])

        # Name
        description_string = ffi.string(
            pango.pango_font_description_to_string(description))
        fields = description_string.split(b' ')
        if fields and b'=' in fields[-1]:
            fields.pop()  # Remove variations
        if fields:
            fields.pop()  # Remove font size
        else:
            fields = [b'Unknown']
        self.name = b'/' + self.hash.encode() + b'+' + b'-'.join(fields)

        # Ascent & descent
        if font_size:
            self.ascent = int(
                pango.pango_font_metrics_get_ascent(pango_metrics) /
                font_size * 1000)
            self.descent = -int(
                pango.pango_font_metrics_get_descent(pango_metrics) /
                font_size * 1000)
        else:
            self.ascent = self.descent = 0

        # Fonttools
        full_font = io.BytesIO(self.file_content)
        try:
            self.ttfont = TTFont(full_font, fontNumber=self.index)
        except Exception:
            LOGGER.warning('Unable to read font')
            self.ttfont = None
            self.bitmap = False
        else:
            self.bitmap = 'EBDT' in self.ttfont and 'EBLC' in self.ttfont

        # Various properties
        self.italic_angle = 0  # TODO: this should be different
        self.upem = harfbuzz.hb_face_get_upem(hb_face)
        self.png = harfbuzz.hb_ot_color_has_png(hb_face)
        self.svg = harfbuzz.hb_ot_color_has_svg(hb_face)
        self.stemv = 80
        self.stemh = 80
        self.bbox = [0, 0, 0, 0]
        self.widths = {}
        self.cmap = {}

        # Font flags
        self.flags = 2 ** (3 - 1)  # Symbolic, custom character set
        if self.style:
            self.flags += 2 ** (7 - 1)  # Italic
        if b'Serif' in self.family.split():
            self.flags += 2 ** (2 - 1)  # Serif
        widths = self.widths.values()
        if len(widths) > 1 and len(set(widths)) == 1:
            self.flags += 2 ** (1 - 1)  # FixedPitch

    def clean(self, cmap):
        if self.ttfont is None:
            return

        if cmap:
            optimized_font = io.BytesIO()
            options = subset.Options(
                retain_gids=True, passthrough_tables=True,
                ignore_missing_glyphs=True, hinting=False)
            options.drop_tables += ['GSUB', 'GPOS', 'SVG']
            subsetter = subset.Subsetter(options)
            subsetter.populate(gids=cmap)
            try:
                subsetter.subset(self.ttfont)
            except TTLibError:
                LOGGER.warning('Unable to optimize font')
            else:
                self.ttfont.save(optimized_font)
                self.file_content = optimized_font.getvalue()

        if not (self.png or self.svg):
            return

        try:
            # Add empty glyphs instead of PNG or SVG emojis
            if 'loca' not in self.ttfont or 'glyf' not in self.ttfont:
                self.ttfont['loca'] = ttFont.getTableClass('loca')()
                self.ttfont['glyf'] = ttFont.getTableClass('glyf')()
                self.ttfont['glyf'].glyphOrder = self.ttfont.getGlyphOrder()
                self.ttfont['glyf'].glyphs = {
                    name: ttFont.getTableModule('glyf').Glyph()
                    for name in self.ttfont['glyf'].glyphOrder}
            else:
                for glyph in self.ttfont['glyf'].glyphs:
                    self.ttfont['glyf'][glyph] = (
                        ttFont.getTableModule('glyf').Glyph())
            for table_name in ('CBDT', 'CBLC', 'SVG '):
                if table_name in self.ttfont:
                    del self.ttfont[table_name]
            output_font = io.BytesIO()
            self.ttfont.save(output_font)
            self.file_content = output_font.getvalue()
        except TTLibError:
            LOGGER.warning('Unable to save emoji font')

    @property
    def type(self):
        return 'otf' if self.file_content[:4] == b'OTTO' else 'ttf'


class Stream(pydyf.Stream):
    """PDF stream object with extra features."""
    def __init__(self, fonts, page_rectangle, states, x_objects, patterns,
                 shadings, images, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.compress = True
        self.page_rectangle = page_rectangle
        self._fonts = fonts
        self._states = states
        self._x_objects = x_objects
        self._patterns = patterns
        self._shadings = shadings
        self._images = images
        self._current_color = self._current_color_stroke = None
        self._current_alpha = self._current_alpha_stroke = None
        self._current_font = self._current_font_size = None
        self._old_font = self._old_font_size = None
        self._ctm_stack = [Matrix()]

        # These objects are used in text.show_first_line
        self.length = ffi.new('unsigned int *')
        self.ink_rect = ffi.new('PangoRectangle *')
        self.logical_rect = ffi.new('PangoRectangle *')
        self.hb_extents = ffi.new('hb_glyph_extents_t *')

    @property
    def ctm(self):
        return self._ctm_stack[-1]

    def push_state(self):
        super().push_state()
        self._ctm_stack.append(self.ctm)

    def pop_state(self):
        super().pop_state()
        self._current_color = self._current_color_stroke = None
        self._current_alpha = self._current_alpha_stroke = None
        self._current_font = None
        self._ctm_stack.pop()
        assert self._ctm_stack

    def transform(self, a=1, b=0, c=0, d=1, e=0, f=0):
        super().transform(a, b, c, d, e, f)
        self._ctm_stack[-1] = Matrix(a, b, c, d, e, f) @ self.ctm

    def begin_text(self):
        if self.stream and self.stream[-1] == b'ET':
            self._current_font = self._old_font
            self.stream.pop()
        else:
            super().begin_text()

    def end_text(self):
        self._old_font, self._current_font = self._current_font, None
        super().end_text()

    def set_color_rgb(self, r, g, b, stroke=False):
        if stroke:
            if (r, g, b) == self._current_color_stroke:
                return
            else:
                self._current_color_stroke = (r, g, b)
        else:
            if (r, g, b) == self._current_color:
                return
            else:
                self._current_color = (r, g, b)

        super().set_color_rgb(r, g, b, stroke)

    def set_font_size(self, font, size):
        if (font, size) == self._current_font:
            return
        self._current_font = (font, size)
        super().set_font_size(font, size)

    def set_state(self, state):
        key = f's{len(self._states)}'
        self._states[key] = state
        super().set_state(key)

    def set_alpha(self, alpha, stroke=False, fill=None):
        if fill is None:
            fill = not stroke

        if stroke:
            key = f'A{alpha}'
            if key != self._current_alpha_stroke:
                self._current_alpha_stroke = key
                if key not in self._states:
                    self._states[key] = pydyf.Dictionary({'CA': alpha})
                super().set_state(key)

        if fill:
            key = f'a{alpha}'
            if key != self._current_alpha:
                self._current_alpha = key
                if key not in self._states:
                    self._states[key] = pydyf.Dictionary({'ca': alpha})
                super().set_state(key)

    def set_alpha_state(self, x, y, width, height):
        alpha_stream = self.add_group((x, y, width, height))
        alpha_state = pydyf.Dictionary({
            'Type': '/ExtGState',
            'SMask': pydyf.Dictionary({
                'Type': '/Mask',
                'S': '/Luminosity',
                'G': alpha_stream,
            }),
            'ca': 1,
            'AIS': 'false',
        })
        self.set_state(alpha_state)
        return alpha_stream

    def set_blend_mode(self, mode):
        self.set_state(pydyf.Dictionary({
            'Type': '/ExtGState',
            'BM': f'/{mode}',
        }))

    def add_font(self, pango_font):
        hb_font = pango.pango_font_get_hb_font(pango_font)
        hb_face = harfbuzz.hb_font_get_face(hb_font)
        if hb_face not in self._fonts:
            self._fonts[hb_face] = Font(pango_font, hb_face)
        return self._fonts[hb_face]

    def add_group(self, bounding_box):
        states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        resources = pydyf.Dictionary({
            'ExtGState': states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
            'Font': None,  # Will be set by _use_references
        })
        extra = pydyf.Dictionary({
            'Type': '/XObject',
            'Subtype': '/Form',
            'BBox': pydyf.Array(bounding_box),
            'Resources': resources,
            'Group': pydyf.Dictionary({
                'Type': '/Group',
                'S': '/Transparency',
                'I': 'true',
                'CS': '/DeviceRGB',
            }),
        })
        group = Stream(
            self._fonts, self.page_rectangle, states, x_objects, patterns,
            shadings, self._images, extra=extra)
        group.id = f'x{len(self._x_objects)}'
        self._x_objects[group.id] = group
        return group

    def _get_png_data(self, pillow_image, optimize):
        image_file = io.BytesIO()
        pillow_image.save(image_file, format='PNG', optimize=optimize)

        # Read the PNG header, then discard it because we know it's a PNG. If
        # this weren't just output from Pillow, we should actually check it.
        image_file.seek(8)

        png_data = b''
        raw_chunk_length = image_file.read(4)
        # PNG files consist of a series of chunks.
        while len(raw_chunk_length) > 0:
            # Each chunk begins with its data length (four bytes, may be zero),
            # then its type (four ASCII characters), then the data, then four
            # bytes of a CRC.
            chunk_len, = struct.unpack('!I', raw_chunk_length)
            chunk_type = image_file.read(4)
            if chunk_type == b'IDAT':
                png_data += image_file.read(chunk_len)
            else:
                image_file.seek(chunk_len, io.SEEK_CUR)
            # We aren't checking the CRC, we assume this is a valid PNG.
            image_file.seek(4, io.SEEK_CUR)
            raw_chunk_length = image_file.read(4)

        return png_data

    def add_image(self, pillow_image, image_rendering, optimize_size):
        image_name = f'i{pillow_image.id}'
        self._x_objects[image_name] = None  # Set by write_pdf
        if image_name in self._images:
            # Reuse image already stored in document
            return image_name

        if 'transparency' in pillow_image.info:
            pillow_image = pillow_image.convert('RGBA')
        elif pillow_image.mode in ('1', 'P', 'I'):
            pillow_image = pillow_image.convert('RGB')

        if pillow_image.mode in ('RGB', 'RGBA'):
            color_space = '/DeviceRGB'
        elif pillow_image.mode in ('L', 'LA'):
            color_space = '/DeviceGray'
        elif pillow_image.mode == 'CMYK':
            color_space = '/DeviceCMYK'
        else:
            LOGGER.warning('Unknown image mode: %s', pillow_image.mode)
            color_space = '/DeviceRGB'

        interpolate = 'true' if image_rendering == 'auto' else 'false'
        extra = pydyf.Dictionary({
            'Type': '/XObject',
            'Subtype': '/Image',
            'Width': pillow_image.width,
            'Height': pillow_image.height,
            'ColorSpace': color_space,
            'BitsPerComponent': 8,
            'Interpolate': interpolate,
        })

        optimize = 'images' in optimize_size
        if pillow_image.format == 'JPEG':
            extra['Filter'] = '/DCTDecode'
            image_file = io.BytesIO()
            pillow_image.save(image_file, format='JPEG', optimize=optimize)
            stream = [image_file.getvalue()]
        else:
            extra['Filter'] = '/FlateDecode'
            extra['DecodeParms'] = pydyf.Dictionary({
                # Predictor 15 specifies that we're providing PNG data,
                # ostensibly using an "optimum predictor", but doesn't actually
                # matter as long as the predictor value is 10+ according to the
                # spec. (Other PNG predictor values assert that we're using
                # specific predictors that we don't want to commit to, but
                # "optimum" can vary.)
                'Predictor': 15,
                'Columns': pillow_image.width,
            })
            if pillow_image.mode in ('RGB', 'RGBA'):
                # Defaults to 1.
                extra['DecodeParms']['Colors'] = 3
            if pillow_image.mode in ('RGBA', 'LA'):
                alpha = pillow_image.getchannel('A')
                pillow_image = pillow_image.convert(pillow_image.mode[:-1])
                alpha_data = self._get_png_data(alpha, optimize)
                extra['SMask'] = pydyf.Stream([alpha_data], extra={
                    'Filter': '/FlateDecode',
                    'Type': '/XObject',
                    'Subtype': '/Image',
                    'DecodeParms': pydyf.Dictionary({
                        'Predictor': 15,
                        'Columns': pillow_image.width,
                    }),
                    'Width': pillow_image.width,
                    'Height': pillow_image.height,
                    'ColorSpace': '/DeviceGray',
                    'BitsPerComponent': 8,
                    'Interpolate': interpolate,
                    })
            stream = [self._get_png_data(pillow_image, optimize)]

        xobject = pydyf.Stream(stream, extra=extra)
        self._images[image_name] = xobject
        return image_name

    def add_pattern(self, width, height, repeat_width, repeat_height, matrix):
        states = pydyf.Dictionary()
        x_objects = pydyf.Dictionary()
        patterns = pydyf.Dictionary()
        shadings = pydyf.Dictionary()
        resources = pydyf.Dictionary({
            'ExtGState': states,
            'XObject': x_objects,
            'Pattern': patterns,
            'Shading': shadings,
            'Font': None,  # Will be set by _use_references
        })
        extra = pydyf.Dictionary({
            'Type': '/Pattern',
            'PatternType': 1,
            'BBox': pydyf.Array([0, 0, width, height]),
            'XStep': repeat_width,
            'YStep': repeat_height,
            'TilingType': 1,
            'PaintType': 1,
            'Matrix': pydyf.Array(matrix.values),
            'Resources': resources,
        })
        pattern = Stream(
            self._fonts, self.page_rectangle, states, x_objects, patterns,
            shadings, self._images, extra=extra)
        pattern.id = f'p{len(self._patterns)}'
        self._patterns[pattern.id] = pattern
        return pattern

    def add_shading(self, shading_type, color_space, domain, coords, extend,
                    function):
        shading = pydyf.Dictionary({
            'ShadingType': shading_type,
            'ColorSpace': f'/Device{color_space}',
            'Domain': pydyf.Array(domain),
            'Coords': pydyf.Array(coords),
            'Function': function,
        })
        if extend:
            shading['Extend'] = pydyf.Array((b'true', b'true'))
        shading.id = f's{len(self._shadings)}'
        self._shadings[shading.id] = shading
        return shading

    @staticmethod
    def create_interpolation_function(domain, c0, c1, n):
        return pydyf.Dictionary({
            'FunctionType': 2,
            'Domain': pydyf.Array(domain),
            'C0': pydyf.Array(c0),
            'C1': pydyf.Array(c1),
            'N': n,
        })

    @staticmethod
    def create_stitching_function(domain, encode, bounds, sub_functions):
        return pydyf.Dictionary({
            'FunctionType': 3,
            'Domain': pydyf.Array(domain),
            'Encode': pydyf.Array(encode),
            'Bounds': pydyf.Array(bounds),
            'Functions': pydyf.Array(sub_functions),
        })
