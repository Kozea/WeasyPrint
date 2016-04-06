---
layout: page
title: "WeasyPrint 0.16: PDF zoom and bug fixes"
---

A small release this time.

A new `zoom` parameter on PDF output can change
the ratio between CSS length units and PDF units.
The various CSS units however still have the same relative ratios:
a CSS pixel is always one 96th of an inch.
This can be a work-around for using an existing fixed-width CSS layout
on various page sizes.

A few bugs in WeasyPrint were fixed and some in pycairo were worked around.
This restores compatibility with Debian Squeeze and other distributions that
still use broken versions of pycairo.

[Changelog for 0.16](/docs/changelog/#version-0-16).
