#!/usr/bin/env python
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

import gtk
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
    def __init__(self, text, width):
        self.context = gtk.DrawingArea().create_pango_context()
        self.layout = pango.Layout(self.context)
        self.layout.set_text(text.encode("utf-8"))
        self.width = width
        # Other properties
        self.layout.set_wrap(pango.WRAP_WORD)
    
    def _update_font(self):
        self.layout.set_font_description(self._font)
    
    @property
    def availables_font(self):
        for font in gtk.DrawingArea().create_pango_context().list_families():
            yield font.get_name()
    
    @property
    def text(self):
        return self.layout.get_text().decode('utf-8')

    @text.setter
    def text(self, value):
        self.layout.set_text(value.encode("utf-8"))

    @property
    def size(self):
        """ Return the real text area size in px unit """
        return self.layout.get_pixel_size()
    
    @property
    def width(self):
        """ Return the width. It's different to real width of text area """
        return self._width
    
    @width.setter
    def width(self, value):
        self._width = value
        self.layout.set_width(pango.SCALE * value)
    
    @property
    def spacing(self):
        """ Return the spacing. """
        return self.layout.get_spacing() / pango.SCALE
    
    @spacing.setter
    def spacing(self, value):
        self.layout.set_spacing(pango.SCALE * value)
    
    def set_font(self, font_desc):
        self.layout.set_font_description(pango.FontDescription(font_desc))
    
    @property
    def alignment(self):
        alignment = self.layout.get_alignment()
        for key in ALIGN_PROPERTIES:
            if ALIGN_PROPERTIES[key] == alignment:
                return key
    
    @alignment.setter
    def alignment(self, alignment):
        if alignment in ("left", "center", "right"):
            self.layout.set_alignment(ALIGN_PROPERTIES[alignment])
        else:
            raise ValueError('The alignment property must be in %s' \
                % ALIGN_PROPERTIES.keys())

    
    @property
    def justify(self):
        self.layout.get_justify()
    
    @justify.setter
    def justify(self, value):
        self.layout.set_justify(value)
    
    @property
    def font(self):
        self._font = self.layout.get_font_description()
        if self._font is None:
            self._font = self.layout.get_context().get_font_description()
            self.layout.set_font_description(self._font)
        return self._font
    
    @property
    def font_family(self):
        return self.font.get_family().decode('utf-8')
    
    @font_family.setter
    def font_family(self, value):
        self.font.set_family(value.encode("utf-8"))
        self._update_font()
    
    @property
    def font_style(self):
        style = self.font.get_style()
        for key in STYLE_PROPERTIES:
            if STYLE_PROPERTIES[key] == style:
                return key
    
    @font_style.setter
    def font_style(self, value):
        """
        The value of style must be either
        pango.STYLE_NORMAL
        pango.STYLE_ITALIC
        pango.STYLE_OBLIQUE
        but not both >> like cs
        
        ...and font matching in Pango will match italic specifications
        with oblique fonts and vice-versa if an exact match is not found.
        """
        if value in STYLE_PROPERTIES.keys():
            self.font.set_style(value)
            self._update_font()
        else:
            raise ValueError('The style property must be in %s' \
                % STYLE_PROPERTIES.keys())
    
    @property
    def font_size(self):
        return self.font.get_size() / pango.SCALE
    
    @font_size.setter
    def font_size(self, value):
        """The value of size is specified in px units."""
        self.font.set_size(pango.SCALE * value)
        self._update_font()
    
    @property
    def font_variant(self):
        variant = self.font.get_variant()
        for key in VARIANT_PROPERTIES:
            if VARIANT_PROPERTIES[key] == variant:
                return key
    
    @font_variant.setter
    def font_variant(self, value):
        """
        variant : the variant type for the font description.
        The set_variant() method sets the variant attribute field of a font
        description to the value specified by variant. The value of variant
        must be either
        pango.VARIANT_NORMAL
        pango.VARIANT_SMALL_CAPS
        """
        if value in VARIANT_PROPERTIES.keys():
            self.font.set_variant(value)
            self._update_font()
        else:
            raise ValueError('The style property must be in %s' \
                % VARIANT_PROPERTIES.keys())
    
    @property
    def font_weight(self):
        return int(float(self.font.get_weight()))
    
    @font_weight.setter
    def font_weight(self, value):
        """
        The value of weight specifies how bold or light the font should be
        in a range from 100 to 900. The predefined values of weight are :

        pango.WEIGHT_ULTRALIGHT the ultralight weight (= 200)
        pango.WEIGHT_LIGHT the light weight (=300)
        pango.WEIGHT_NORMAL the default weight (= 400)
        pango.WEIGHT_BOLD the bold weight (= 700)
        pango.WEIGHT_HEAVY the heavy weight (= 900)
        pango.WEIGHT_ULTRABOLD the ultrabold weight (= 800)
        """
        self.font.set_weight(value)
        self._update_font()


class LineTextFragment(TextFragment):
    def __init__(self, text, width):
        super(LineTextFragment, self).__init__(text, width)
    
    @property
    def remaining_text(self):
        first_line = self.layout.get_line(0)
        return super(LineTextFragment, self).text[first_line.length:]
    
    @property
    def text(self):
        first_line = self.layout.get_line(0)
        return super(LineTextFragment, self).text[:first_line.length]
    
    @property
    def size(self):
        """ Return the real text area dimension for this line in px unit """
        extents = self.layout.get_line(0).get_pixel_extents()[1]
        return (extents[2]-extents[0], extents[3]-extents[1])
