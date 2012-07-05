#!/bin/sh
cd $(dirname $0)
weasyprint http://www.webstandards.org/files/acid2/test.html acid2.pdf
weasyprint http://www.webstandards.org/files/acid2/test.html acid2.png
weasyprint http://www.w3.org/TR/CSS21/intro.html CSS21-intro.pdf -s CSS21-print.css
