# coding: utf-8
"""
    weasyprint.formatting_structure.rect
    -------------------

    Classes for all types of rectangles to use them easily without remembering
    which position in list is top bottom left and right.

"""

from collections import namedtuple


Rect = namedtuple("Rect", ("top", "right", "bottom", "left"))


class BleedRect(Rect):

    @classmethod
    def from_style(cls, style):
        return cls(
            style['bleed_top'].value,
            style['bleed_right'].value,
            style['bleed_bottom'].value,
            style['bleed_left'].value
        )

    def get_scaled(self, factor):
        return self.__class__(
            self.top * factor,
            self.right * factor,
            self.bottom * factor,
            self.left * factor,
        )

# eof
