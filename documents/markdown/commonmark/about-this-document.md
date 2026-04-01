## About this document


This document attempts to specify Markdown syntax unambiguously.
It contains many examples with side-by-side Markdown and
HTML.  These are intended to double as conformance tests.  An
accompanying script `spec_tests.py` can be used to run the tests
against any Markdown program:

    python test/spec_tests.py --spec spec.txt --program PROGRAM

Since this document describes how Markdown is to be parsed into
an abstract syntax tree, it would have made sense to use an abstract
representation of the syntax tree instead of HTML.  But HTML is capable
of representing the structural distinctions we need to make, and the
choice of HTML for the tests makes it possible to run the tests against
an implementation without writing an abstract syntax tree renderer.

Note that not every feature of the HTML samples is mandated by
the spec.  For example, the spec says what counts as a link
destination, but it doesn't mandate that non-ASCII characters in
the URL be percent-encoded.  To use the automatic tests,
implementers will need to provide a renderer that conforms to
the expectations of the spec examples (percent-encoding
non-ASCII characters in URLs).  But a conforming implementation
can use a different renderer and may choose not to
percent-encode non-ASCII characters in URLs.

This document is generated from a text file, `spec.txt`, written
in Markdown with a small extension for the side-by-side tests.
The script `tools/makespec.py` can be used to convert `spec.txt` into
HTML or CommonMark (which can then be converted into other formats).

In the examples, the `→` character is used to represent tabs.

# Preliminaries

