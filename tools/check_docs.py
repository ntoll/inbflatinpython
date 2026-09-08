"""
Verify the documentation's honesty: every "play it on the
stage" link must carry, in its fragment, exactly the score
its neighbouring code block displays - and that score must
compile. Run from the repository root:

    python tools/check_docs.py

Standard library only; exits non-zero on any disagreement.
"""
import html
import re
import sys
from urllib.parse import unquote

# A block is one pre with no pre-closing inside it. It
# pairs with the first stage link that follows before any
# further code block: prose may sit between the two, but
# another pre may not - a lazy dot here once swallowed
# whole chapters.
PAIR = re.compile(
    r"<pre>\n((?:(?!</pre>).)*)</pre>"
    r"(?:(?!<pre).)*?<p><a[^>]*"
    r"href=\"\.\./\#score=([^\"]+)\"",
    re.S,
)


def shown(block):
    """The code a reader sees: tags stripped, entities
    resolved, incidental trailing whitespace ignored."""
    text = re.sub(r"<[^>]+>", "", block)
    text = html.unescape(text)
    return "\n".join(
        line.rstrip() for line in text.strip().splitlines()
    )


def carried(fragment):
    """The code a link carries, normalised the same way."""
    text = unquote(fragment)
    return "\n".join(
        line.rstrip() for line in text.strip().splitlines()
    )


def main():
    """Check every display/fragment pair in the docs."""
    page = open("docs/index.html").read()
    pairs = PAIR.findall(page)
    links = page.count('href="../#score=')
    trouble = 0
    for number, (block, fragment) in enumerate(pairs, 1):
        display = shown(block)
        travels = carried(fragment)
        if display != travels:
            trouble += 1
            print("pair " + str(number)
                  + ": display and fragment disagree")
        try:
            compile(travels, "pair " + str(number), "exec")
        except SyntaxError as error:
            trouble += 1
            print("pair " + str(number)
                  + ": does not compile - " + str(error))
    print(str(len(pairs)) + " of " + str(links)
          + " stage links paired with a code block and"
          " checked")
    if len(pairs) != links:
        print("warning: " + str(links - len(pairs))
              + " link(s) not adjacent to a code block")
    if trouble:
        print(str(trouble) + " problem(s)")
        return 1
    print("the documentation tells one truth")
    return 0


if __name__ == "__main__":
    sys.exit(main())