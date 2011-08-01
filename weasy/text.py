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

ALIGN_PROPERTIES = {'left':pango.ALIGN_LEFT,
                    'center':pango.ALIGN_RIGHT,
                    'right':pango.ALIGN_CENTER}

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
        self.set_font_size(textbox.style.font_size)
        self.set_alignment(textbox.style.text_align)
        self.set_font_variant(textbox.style.font_variant)
        self.set_font_weight(int(textbox.style.font_weight))
        self.set_font_style(textbox.style.font_style)
        if isinstance(textbox.style.letter_spacing, int):
            self.set_letter_spacing(textbox.style.letter_spacing)
        if textbox.style.text_decoration == "none":
            self.set_underline(False)
            self.set_line_through(False)
            # TODO: Implement overline in TextFragment
            #set_overline(False)
        else:
            if 'overline' in textbox.style.text_decoration:
                # TODO: Implement overline in TextFragment
                #set_overline(False)
                pass
            if 'underline' in textbox.style.text_decoration:
                self.set_underline(True)
            if 'line-through' in textbox.style.text_decoration:
                self.set_line_through(True)
        self.set_foreground(textbox.style.color)
        if textbox.style.background_color != 'transparent':
            self.set_background(textbox.style.color)


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

#    def get_width(self):
#        """ Return the width. It's different to real width of text area """
#        return self._width

    def set_width(self, value):
        """
        Set the desired width, or -1 to indicate that no wrapping should be
        performed.
        """
        if value != -1:
            value = pango.SCALE * value
        self.layout.set_width(int(value))

    def get_spacing(self):
        """Return the horizontal spacing (between the lines). """
        return self.layout.get_spacing() / pango.SCALE

    def set_spacing(self, value):
        """ sets the spacing between the lines of the layout. """
        self.layout.set_spacing(pango.SCALE * value)

    def get_alignment(self):
        """Return the default alignment of text in layout."""
        alignment = self.layout.get_alignment()
        for key in ALIGN_PROPERTIES:
            if ALIGN_PROPERTIES[key] == alignment:
                return key

    def set_alignment(self, alignment):
        """Sets the default alignment of text in layout.
        The value of alignment must be one of : ("left", "center", "right")
        """
        if alignment in ("left", "center", "right"):
            self.layout.set_alignment(ALIGN_PROPERTIES[alignment])
        else:
            raise ValueError('The alignment property must be in %s' \
                % ALIGN_PROPERTIES.keys())

    def get_justify(self):
        """Returns True if the text is justified """
        self.layout.get_justify()

    def set_justify(self, value):
        """Lets make the text justified or not, depending on the value"""
        self.layout.set_justify(value)

    def get_font_family(self):
        """Returns the font family name that used by the pango layout"""
        return self.font.get_family().decode('utf-8')

    def set_font_family(self, value):
        """Sets the font used. VALUE can be a police list of comma-separated,
        as in CSS.
        Eg.
        >> set_font_family("Al Mawash Bold, Comic sans MS")
        """
        self.font.set_family(value.encode("utf-8"))
        self._update_font()

    def get_font_style(self):
        """Returns the font style that used by the pango layout"""
        style = self.font.get_style()
        for key in STYLE_PROPERTIES:
            if STYLE_PROPERTIES[key] == style:
                return key

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

    def get_font_size(self):
        """Returns the font size of text"""
        return self.font.get_size() / pango.SCALE

    def set_font_size(self, value):
        """Sets the font size. The value of size is specified in px units.
        `value` must be an interger.
        """
        self.font.set_size(pango.SCALE * int(value))
        self._update_font()

    def get_font_variant(self):
        """Returns the font variant that used by the pango layout"""
        variant = self.font.get_variant()
        for key in VARIANT_PROPERTIES:
            if VARIANT_PROPERTIES[key] == variant:
                return key

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

    def get_font_weight(self):
        """Returns the font weight that used by the pango layout

        The predefined values of weight are :

        pango.WEIGHT_ULTRALIGHT the ultralight weight (= 200)
        pango.WEIGHT_LIGHT the light weight (=300)
        pango.WEIGHT_NORMAL the default weight (= 400)
        pango.WEIGHT_BOLD the bold weight (= 700)
        pango.WEIGHT_HEAVY the heavy weight (= 900)
        pango.WEIGHT_ULTRABOLD the ultrabold weight (= 800)

        The function returns an integer, and must first convert the value to
        float for a weird reason
        """
        return int(float(self.font.get_weight()))

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
        ls = pango.AttrLetterSpacing(value * pango.SCALE, 0, -1)
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
#        extents = self.layout.get_line(0).get_pixel_extents()[1]
#        return (extents[2]-extents[0], extents[3]-extents[1])
#        TODO: What's the size ? the line's size, or the size of a layoutLine ?
        return self.get_layout().get_pixel_size()

    def get_logical_extents(self):
        """Returns the size of the logical area that occupied by the text"""
        return self.layout.get_line(0).get_pixel_extents()[1]

