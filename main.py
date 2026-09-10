"""
Bootstrap for InB♭InPython: build the editor, wire Play and
Stop, and move between the rehearsal room and the stage.
Each press of Play performs whatever score is currently in
the editor, via exec().
"""
import js
from bfp import web, when, ffi, window
from bfp.js_modules import codemirror as cm
from bfp.js_modules import lang_python
import inbflat

def _shared_score():
    """
    A score carried in the page's fragment (#score=...), as
    the Share button makes. The fragment never reaches the
    server, so performances travel as plain links on any
    static host.
    """
    fragment = window.location.hash
    if fragment.startswith("#score="):
        return window.decodeURIComponent(fragment[7:])
    return None


# A shared score in the URL wins; otherwise the initial
# score is an ordinary file, mapped onto the virtual
# filesystem by the config and read from there.
_score = _shared_score()
if _score is None:
    with open("score.py") as source:
        _score = source.read().strip() + "\n"

# The extensions are a genuine JavaScript Array, built on the
# JS side of the boundary, so CodeMirror's own array checks
# see exactly what they expect.
_extensions = js.Array.of(cm.basicSetup, lang_python.python())

_editor = cm.EditorView.new(
    ffi.to_js({
        "doc": _score,
        "extensions": _extensions,
        "parent": web.page["editor"]._dom_element,
    })
)


def _report(trouble):
    """
    Explain a broken score kindly, back in the rehearsal
    room where the performer can fix it.
    """
    web.page["errors"].textContent = (
        "The score could not be performed - "
        + type(trouble).__name__ + ": " + str(trouble)
    )


@when("click", "#play")
def start(event):
    """Fade to the stage and perform the editor's score."""
    inbflat.clear()
    web.page["errors"].textContent = ""
    web.page.body.classes.add("performing")
    try:
        exec(_editor.state.doc.toString(), {})
    except Exception as trouble:
        web.page.body.classes.remove("performing")
        _report(trouble)


@when("click", "#stop")
def stop(event):
    """End the performance; fade back to the rehearsal room."""
    inbflat.clear()
    web.page.body.classes.remove("performing")


@when("click", "#share")
def share(event):
    """
    Copy a link carrying the editor's score in its
    fragment: a performance becomes a URL, and the page's
    own address is left in peace.
    """
    encoded = window.encodeURIComponent(
        _editor.state.doc.toString()
    )
    link = window.location.href.split("#")[0]
    window.navigator.clipboard.writeText(
        link + "#score=" + encoded
    )
    web.page["share-note"].textContent = (
        "Link copied to clipboard."
    )


# Boot is done: the editor is built and every control is
# wired, so Play and Share wake and the notice clears.
web.page["play"]._dom_element.disabled = False
web.page["share"]._dom_element.disabled = False
web.page["share-note"].textContent = ""