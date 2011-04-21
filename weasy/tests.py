# coding: utf8

from attest import Tests, assert_hook
from lxml import html
#from lxml.html import html5parser as html  # API is the same as lxml.html


tests = Tests()


@tests.test
def foo():
    source = u"<p>今日は html5lib!"
#    doc = html5lib.parse(source, treebuilder="lxml")
    doc = html.document_fromstring(source)
#    print type(doc), repr(doc), str(doc), dir(doc)

    assert 2 + 2 == 5
    

