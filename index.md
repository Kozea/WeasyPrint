---
layout: page
title: WeasyPrint converts HTML/CSS documents to PDF
permalink: /
---

WeasyPrint is a visual rendering engine for HTML and CSS that can export
to PDF. It aims to support web standards for printing.
WeasyPrint is free software made available under a BSD license.

It is based on various libraries but *not* on a full rendering engine like
WebKit or Gecko. The CSS layout engine is written in Python, designed for
pagination, and meant to be easy to hack on.

* Free software: BSD licensed
* Python 2.6+ or 3.x
* Source code and issue tracker: [on Github](https://github.com/Kozea/WeasyPrint)
* [Documentation](http://weasyprint.readthedocs.org/en/latest/)
  - [Install](http://weasyprint.readthedocs.org/en/latest/install.html)
  - [Features](http://weasyprint.readthedocs.org/en/latest/features.html)
* [Get in touch](/community/)


## Sample output

As an example, here is the
[introduction chapter](http://www.w3.org/TR/CSS21/intro.html) of the CSS 2.1
spec rendered with WeasyPrint: [CSS21-intro.pdf](/samples/CSS21-intro.pdf). It
was obtained by running:

```
weasyprint http://www.w3.org/TR/CSS21/intro.html CSS21-intro.pdf -s http://weasyprint.org/samples/CSS21-print.css
```

Here is an extract of [CSS21-print.css](/samples/CSS21-print.css):

```scss
@page {
    margin: 3cm 2cm; padding-left: 1.5cm;
    @top-center {
        content: "Introduction to CSS 2.1";
        vertical-align: bottom;
        border-bottom: 0.5pt solid }
    @bottom-right {
        content: "Page " counter(page)
                 " of " counter(pages) }
    @left-top {
        content: "W3C Recommendation";
        background: #005a9c;
        color: #fff;
        text-align: right;
        transform-origin: 100% 0;
        transform: rotate(-90deg) }}
body { text-align: justify }
h1 { -weasy-bookmark-level: none }
```


## Acid2

![Acid2](/samples/acid2-small.png)

Starting with version 0.11, WeasyPrint passes the
[Acid2](http://www.webstandards.org/files/acid2/test.html) test. This test was
published by the
[Web Standards Project](http://www.webstandards.org/action/acid2/) as a
challenge for web browser to get better support for the HTML, CSS and PNG
standards. It is made of many small elements with various positioning
techniques. When all the layout rules are implemented correctly, they should
add up to the smiling face shown on the right.

Have a look at WeasyPrint’s output [in PDF](/samples/acid2.pdf) and
[in PNG](/samples/acid2.png). The PNG is pixel-perfect, but with PDF you may
see faint lines or a [moiré](https://en.wikipedia.org/wiki/Moir%C3%A9) pattern
inside the smiling head. This is because the test is made for pixel-based
screens with many layers of different colors that overlap exactly. Only the top
layers are supposed to be visible but due to the way that most PDF viewers use
anti-aliasing, the bottom layers may bleed on the sides.
