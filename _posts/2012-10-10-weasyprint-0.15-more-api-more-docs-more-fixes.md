---
layout: page
title: "WeasyPrint 0.15: More API, more docs, more fixes"
---

0.15 is (finally!) out. This one is light in CSS features, but
[Sphinx-based documentation](/docs/) as well as a new API with low-level access
to individual pages.

**Backward-incompatible change**: the `HTML.get_png_pages()` method is gone,
it was ridiculously specific compared to the new API. It can be reproduced
like this:

```python
def get_png_pages(document):
    """Yield (png_bytes, width, height) tuples."""
    for page in document.pages:
        yield document.copy([page]).write_png()
```

[Changelog for 0.15](/docs/changelog/#version-0-15).
