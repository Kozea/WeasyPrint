# coding: utf8
#  WeasyPrint converts web documents (HTML, CSS, ...) to PDF.
#  Copyright (C) 2011  Simon Sapin
#
#  This program is free software: you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as
#  published by the Free Software Foundation, either version 3 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program.  If not, see <http://www.gnu.org/licenses/>.

import cairo
import pangocairo
import pango

from .css.values import get_single_keyword, get_keyword, get_single_pixel_value


ALIGN_PROPERTIES = {'left':pango.ALIGN_LEFT,
                    'right':pango.ALIGN_RIGHT,
                    'center':pango.ALIGN_CENTER}

STYLE_PROPERTIES = {'normal':pango.STYLE_NORMAL,
                    'italic':pango.STYLE_ITALIC,
                    'oblique':pango.STYLE_OBLIQUE}

VARIANT_PROPERTIES = {'normal':pango.VARIANT_NORMAL,
                     'small-caps':pango.VARIANT_SMALL_CAPS}


class TextFragment(object):
    """
    TextFragment is a class that provides simple methods for rendering text
    with pango, especially from a TextBox
    """
    def __init__(self, text="", width=-1, surface=None):
        if surface is None:
            surface = cairo.ImageSurface(cairo.FORMAT_ARGB32, 400, 400)
        cr = pangocairo.CairoContext(cairo.Context(surface))
        self.layout = cr.create_layout()
        self.set_text(text)
        self.set_width(width)
        # If fallback is True other fonts on the system can be used to provide
        # characters missing from the current font. Otherwise, only characters
        # from the closest matching font can be used.
        #
        # See : http://www.pygtk.org/docs/pygtk/class-pangoattribute.html
        self._set_attribute(pango.AttrFallback(True, 0, -1))
        # Other properties
        self.layout.set_wrap(pango.WRAP_WORD)

    def set_textbox(self, textbox):
        """Sets textbox properties in pango layout"""
        self.set_text(textbox.text)
        font = ', '.join(v.cssText for v in textbox.style['font-family'])
        self.set_font_family(font)
        self.set_font_size(get_single_pixel_value(textbox.style.font_size))
        self.set_alignment(get_single_keyword(textbox.style.text_align))
        self.set_font_variant(get_single_keyword(textbox.style.font_variant))
        self.set_font_weight(int(textbox.style.font_weight[0].value))
        self.set_font_style(get_single_keyword(textbox.style.font_style))
        letter_spacing = get_single_pixel_value(textbox.style.letter_spacing)
        if letter_spacing is not None:
            self.set_letter_spacing(letter_spacing)
        if get_single_keyword(textbox.style.text_decoration) == "none":
            self.set_underline(False)
            self.set_line_through(False)
            # TODO: Implement overline in TextFragment
            #set_overline(False)
        else:
            values = textbox.style.text_decoration
            for value in values:
                keyword = get_keyword(value)
                if keyword == 'overline':
                    # TODO: Implement overline in TextFragment
                    #set_overline(False)
                    pass
                elif keyword == 'underline':
                    self.set_underline(True)
                elif keyword == 'line-through':
                    self.set_line_through(True)
                else:
                    raise ValueError('text-decoration: %r' % values)
        self.set_foreground(textbox.style.color[0].cssText)
        background = textbox.style.background_color[0]
        if background.alpha > 0:
            self.set_background(background.cssText)


    @classmethod
    def from_textbox(cls, textbox):
        """Make a TextFragment from an TextBox"""
        surface = textbox.document.surface
        object_cls = cls("", -1, surface)
        object_cls.set_textbox(textbox)
        return object_cls

    def _update_font(self):
        self.layout.set_font_description(self._font)

    def _get_attributes(self):
        attributes = self.layout.get_attributes()
        if attributes:
            return attributes
        else:
            return pango.AttrList()

    def _set_attribute(self, value):
        attributes = self.layout.get_attributes()
        if attributes:
            try:
                attributes.change(value)
            except:
                attributes.insert(value)
        else:
            attributes = pango.AttrList()
            attributes.insert(value)
        self.layout.set_attributes(attributes)

    def get_layout(self):
        return self.layout.copy()

    @property
    def font(self):
        self._font = self.layout.get_font_description()
        if self._font is None:
            self._font = self.layout.get_context().get_font_description()
        return self._font

    @font.setter
    def font(self, font_desc):
        self.layout.set_font_description(pango.FontDescription(font_desc))

    def get_text(self):
        return self.layout.get_text().decode('utf-8')

    def set_text(self, value):
        self.layout.set_text(value.encode("utf-8"))

    def get_size(self):
        """ Return the real text area size in px unit """
        return self.layout.get_pixel_size()

    def set_width(self, value):
        """
        Set the desired width, or -1 to indicate that no wrapping should be
        performed.
        """
        if value != -1:
            value = pango.SCALE * value
        self.layout.set_width(int(value))

    def set_spacing(self, value):
        """ sets the spacing between the lines of the layout. """
        self.layout.set_spacing(pango.SCALE * value)

    def set_alignment(self, alignment):
        """Sets the default alignment of text in layout.
        The value of alignment must be one of : ("left", "center", "right")
        """
        if alignment == 'justify':
            self.layout.set_alignment(ALIGN_PROPERTIES['left'])
            self.layout.set_justify(True)
        else:
            self.layout.set_alignment(ALIGN_PROPERTIES[alignment])

    def set_font_family(self, value):
        """Sets the font used. VALUE can be a police list of comma-separated,
        as in CSS.
        Eg.
        >> set_font_family("Al Mawash Bold, Comic sans MS")
        """
        self.font.set_family(value.encode("utf-8"))
        self._update_font()

    def set_font_style(self, value):
        """Sets the font style of text for pango layout.
        The value must be one of : ("normal", "italic", "oblique") like css
        """
        if value in STYLE_PROPERTIES.keys():
            self.font.set_style(STYLE_PROPERTIES[value])
            self._update_font()
        else:
            raise ValueError('The style property must be in %s' \
                % STYLE_PROPERTIES.keys())

    def set_font_size(self, value):
        """Sets the font size. The value of size is specified in px units.
        `value` must be an interger.
        """
        self.font.set_size(pango.SCALE * int(value))
        self._update_font()


    def set_font_variant(self, value):
        """Sets the font variant of text for pango layout.
        The value of variant must be either : ("normal", "small-caps")
        """
        if value in VARIANT_PROPERTIES.keys():
            self.font.set_variant(VARIANT_PROPERTIES[value])
            self._update_font()
        else:
            raise ValueError('The style property must be in %s' \
                % VARIANT_PROPERTIES.keys())

    def set_font_weight(self, value):
        """
        Sets the font variant of text for pango layout.
        The value of variant must be an integer in a range from 100 to 900
        """
        self.font.set_weight(value)
        self._update_font()

    def get_color(self, spec):
        """
        Makes a pango color object from a spec string
        The string in spec can either one of a large set of standard names
        (Taken from the X11 rgb.txt file), or it can be a hex value in the form
        'rgb' 'rrggbb' 'rrrgggbbb' or 'rrrrggggbbbb' where 'r', 'g' and 'b' are
        hex digits of the red, green, and blue components of the color,
        respectively. (White in the four forms is 'fff' 'ffffff' 'fffffffff'
        and 'ffffffffffff')
        """
        return pango.Color(spec)

    def set_foreground(self, spec):
        """Specifies the color of the foreground"""
        color = self.get_color(spec)
        fg_color = pango.AttrForeground(color.red,color.green,color.blue,0,-1)
        self._set_attribute(fg_color)

    def set_background(self, spec):
        """Specifies the color of the background"""
        color = self.get_color(spec)
        bg_color = pango.AttrBackground(color.red,color.green,color.blue,0,-1)
        self._set_attribute(bg_color)

    def set_underline(self, boolean):
        """Serves to underline the text or not depending on the boolean"""
        if boolean:
            underline = pango.AttrUnderline(pango.UNDERLINE_SINGLE, 0, -1)
        else:
            underline = pango.AttrUnderline(pango.UNDERLINE_NONE, 0, -1)
        self._set_attribute(underline)

    def set_overline(self, boolean):
        """Serves to overline the text or not depending on the boolean"""
        raise NotImplementedError("Overline is not implemented yet")

    def set_line_through(self, boolean):
        """Serves to make strikethrough the text, depending on the boolean"""
        self._set_attribute(pango.AttrStrikethrough(boolean, 0, -1))

    def set_underline_color(self, spec):
        """Specifies the underline color"""
        color = self.get_color(spec)
        color = pango.AttrUnderlineColor(color.red, color.blue, color.green,
                                            0, -1)
        self._set_attribute(color)

    def set_line_through_color(self, spec):
        """Specifies the line through color"""
        color = self.get_color(spec)
        color = pango.AttrStrikethroughColor(color.red,color.blue,color.green,
                                            0, -1)
        self._set_attribute(color)

    def set_letter_spacing(self, value):
        """Sets the value of letter spacing"""
        ls = pango.AttrLetterSpacing(int(value * pango.SCALE), 0, -1)
        self._set_attribute(ls)

    def set_rise(self, value):
        """Specifies the text displacement from the baseline"""
        rise = pango.AttrRise(value * pango.SCALE, 0,1)
        self._set_attribute(rise)

class TextLineFragment(TextFragment):
    def __init__(self, text="", width=-1, surface=None):
        super(TextLineFragment, self).__init__(text, width, surface)

    def get_layout_line(self):
        """Make a new layout from the text one line"""
        layout = super(TextLineFragment, self).get_layout()
        layout.set_text(self.get_text())
        return layout

    def get_remaining_text(self):
        """Gets the remaining text that can't be on the line"""
        first_line = self.layout.get_line(0)
        return self.layout.get_text()[first_line.length:].decode('utf-8')

    def get_text(self):
        """Gets all the text can be on the line"""
        first_line = self.layout.get_line(0)
        return self.layout.get_text()[:first_line.length].decode('utf-8')

    def get_size(self):
        """Gets the real text area dimensions for this line in px unit"""
        return self.get_layout().get_pixel_size()

    def get_logical_extents(self):
        """Returns the size of the logical area that occupied by the text"""
        return self.layout.get_line(0).get_pixel_extents()[1]

    def get_baseline(self):
        descent = pango.DESCENT(self.get_logical_extents())
        height = self.get_size()[1]
        return height - descent

