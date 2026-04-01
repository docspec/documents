## Soft line breaks


A regular line ending (not in a code span or HTML tag) that is not
preceded by two or more spaces or a backslash is parsed as a
[softbreak](@).  (A soft line break may be rendered in HTML either as a
[line ending] or as a space. The result will be the same in
browsers. In the examples here, a [line ending] will be used.)

```````````````````````````````` example
foo
baz
.
<p>foo
baz</p>
````````````````````````````````


Spaces at the end of the line and beginning of the next line are
removed:

```````````````````````````````` example
foo 
 baz
.
<p>foo
baz</p>
````````````````````````````````


A conforming parser may render a soft line break in HTML either as a
line ending or as a space.

A renderer may also provide an option to render soft line breaks
as hard line breaks.

