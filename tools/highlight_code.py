"""
Colour a code fragment the way the documentation does.

The documentation's code blocks are Pygments HTML spans,
coloured by the token rules committed in style.css. This
recipe regenerates such spans, so an edited or new block
need never go mysteriously monochrome. Requires Pygments
(pip install pygments). Run from anywhere:

    python tools/highlight_code.py fragment.py
    python tools/highlight_code.py --html fragment.html

Reads the named file - or standard input, given no name -
and prints the highlighted HTML, ready to paste between a
block's <pre> tags in docs/index.html. Afterwards, run
tools/check_docs.py as usual.
"""
import argparse
import sys

from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import HtmlLexer, PythonLexer


def main():
    """Highlight one fragment from a file or stdin."""
    parser = argparse.ArgumentParser(
        description="Colour a code fragment for the docs."
    )
    parser.add_argument(
        "path", nargs="?",
        help="the fragment to colour (stdin if omitted)",
    )
    parser.add_argument(
        "--html", action="store_true",
        help="the fragment is HTML rather than Python",
    )
    options = parser.parse_args()
    if options.path:
        with open(options.path) as fragment:
            code = fragment.read()
    else:
        code = sys.stdin.read()
    lexer = HtmlLexer() if options.html else PythonLexer()
    formatter = HtmlFormatter(nowrap=True)
    sys.stdout.write(highlight(code, lexer, formatter))


if __name__ == "__main__":
    main()
