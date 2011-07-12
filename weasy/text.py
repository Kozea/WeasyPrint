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
    def __init__(self, text="", width=None):
        self.context = gtk.DrawingArea().create_pango_context()
        self.layout = pango.Layout(self.context)
        self.set_text(text)
        if width is not None:
            self.set_width(width)
#        self._set_attribute(pango.AttrFallback(True, 0, -1))
        
        # Other properties
        self.layout.set_wrap(pango.WRAP_WORD)
    
    def set_textbox(self, textbox):
        self.set_text(textbox.text)
#        self.set_font_family(textbox.style.property['font_family'])
#        self.set_font_variant(textbox.style.property['font_family'])
#        self.set_font_weight(textbox.style.property['font_family'])
#        self.set_font_style(textbox.style.property['font_family'])
#        self.set_letter_spacing(textbox.style.property['font_family'])
    
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
    
    def get_availables_font(self):
        for font in gtk.DrawingArea().create_pango_context().list_families():
            yield font.get_name()
    
    def get_text(self):
        return self.layout.get_text().decode('utf-8')
    
    def set_text(self, value):
        self.layout.set_text(value.encode("utf-8"))
    
    def get_size(self):
        """ Return the real text area size in px unit """
        return self.layout.get_pixel_size()
    
    def get_width(self):
        """ Return the width. It's different to real width of text area """
        return self._width
    
    def set_width(self, value):
        self._width = value
        self.layout.set_width(pango.SCALE * value)
    
    def get_spacing(self):
        """ Return the spacing. """
        return self.layout.get_spacing() / pango.SCALE
    
    def set_spacing(self, value):
        self.layout.set_spacing(pango.SCALE * value)
    
    def get_alignment(self):
        alignment = self.layout.get_alignment()
        for key in ALIGN_PROPERTIES:
            if ALIGN_PROPERTIES[key] == alignment:
                return key
    
    def set_alignment(self, alignment):
        if alignment in ("left", "center", "right"):
            self.layout.set_alignment(ALIGN_PROPERTIES[alignment])
        else:
            raise ValueError('The alignment property must be in %s' \
                % ALIGN_PROPERTIES.keys())
    
    def get_justify(self):
        self.layout.get_justify()
    
    def set_justify(self, value):
        self.layout.set_justify(value)
    
    def get_font_family(self):
        return self.font.get_family().decode('utf-8')
    
    def set_font_family(self, value):
        """ 
        value is list of font like this :
        set_font_family("Al Mawash Bold, Comic sans MS")
        """
        self.font.set_family(value.encode("utf-8"))
        self._update_font()
    
    def get_font_style(self):
        style = self.font.get_style()
        for key in STYLE_PROPERTIES:
            if STYLE_PROPERTIES[key] == style:
                return key
    
    def set_font_style(self, value):
        """
        The value of style must be either
        pango.STYLE_NORMAL
        pango.STYLE_ITALIC
        pango.STYLE_OBLIQUE
        but not both >> like css
        
        ...and font matching in Pango will match italic specifications
        with oblique fonts and vice-versa if an exact match is not found.
        """
        if value in STYLE_PROPERTIES.keys():
            self.font.set_style(value)
            self._update_font()
        else:
            raise ValueError('The style property must be in %s' \
                % STYLE_PROPERTIES.keys())
    
    def get_font_size(self):
        return self.font.get_size() / pango.SCALE
    
    def set_font_size(self, value):
        """The value of size is specified in px units."""
        self.font.set_size(pango.SCALE * value)
        self._update_font()
    
    def get_font_variant(self):
        variant = self.font.get_variant()
        for key in VARIANT_PROPERTIES:
            if VARIANT_PROPERTIES[key] == variant:
                return key
    
    def set_font_variant(self, value):
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
    
    def get_font_weight(self):
        return int(float(self.font.get_weight()))
    
    def set_font_weight(self, value):
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
    
    def set_foreground(self, spec):
        """ 
        The string in spec can either one of a large set of standard names.
        (Taken from the X11 rgb.txt file), or it can be a hex value in the
        form 'rgb' 'rrggbb' 'rrrgggbbb' or 'rrrrggggbbbb' where 'r', 'g' and
        'b' are hex digits of the red, green, and blue components of the
        color, respectively. (White in the four forms is 'fff' 'ffffff'
        'fffffffff' and 'ffffffffffff')
        """
        color = pango.Color(spec)
        fg_color = pango.AttrForeground(color.red, color.blue, color.green,
                                            0, -1)
        self._set_attribute(fg_color)
    
    def set_background(self, spec):
        color = pango.Color(spec)
        bg_color = pango.AttrBackground(color.red, color.blue, color.green,
                                            0, -1)
        self._set_attribute(bg_color)
    
    def set_underline(self, boolean):
        if boolean:
            underline = pango.AttrUnderline(pango.UNDERLINE_SINGLE, 0, -1)
        else:
            underline = pango.AttrUnderline(pango.UNDERLINE_NONE, 0, -1)
        self._set_attribute(underline)
    
    def set_overline(self, boolean):
        raise NotImplemented("Overline is not implemented in pango ?")
    
    def set_line_through(self, boolean):
        self._set_attribute(pango.AttrStrikethrough(boolean, 0, -1))
    
    def set_underline_color(self, spec):
        color = pango.Color(spec)
        color = pango.AttrUnderlineColor(color.red, color.blue, color.green,
                                            0, -1)
        self._set_attribute(color)
    
    def set_line_through_color(self, spec):
        color = pango.Color(spec)
        color = pango.AttrStrikethroughColor(color.red,color.blue,color.green,
                                            0, -1)
        self._set_attribute(color)
    
    def set_letter_spacing(self, value):
        ls = pango.AttrLetterSpacing(value * pango.SCALE, 0, -1)
        self._set_attribute(ls)
    
    def set_rise(self, value):
        rise = pango.AttrRise(value * pango.SCALE, 0,1)
        self._set_attribute(rise)
    
class TextLineFragment(TextFragment):
    def __init__(self, text=None, width=None):
        super(TextLineFragment, self).__init__(text, width)

    def get_layout(self):
        layout = super(TextLineFragment, self).get_layout()
        layout.set_text(self.get_text())
        return layout
    
    def get_parent_layout(self):
        return super(TextLineFragment, self).get_layout()

    def get_remaining_text(self):
        first_line = self.layout.get_line(0)
        return super(TextLineFragment, self).get_text()[first_line.length:]
    
    def get_text(self):
        first_line = self.layout.get_line(0)
        return super(TextLineFragment, self).get_text()[:first_line.length]
    
    def get_size(self):
        """ Return the real text area dimension for this line in px unit """
#        extents = self.layout.get_line(0).get_pixel_extents()[1]
#        return (extents[2]-extents[0], extents[3]-extents[1])
        # What's the size ? the size of the line, or the size of a layoutLine ?
        return self.get_layout().get_pixel_size()
    
    def get_logical_extents(self):
        return self.layout.get_line(0).get_pixel_extents()[1]
