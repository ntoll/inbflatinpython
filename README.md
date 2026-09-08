# InB♭InPython

A remix, in Python, of Darren Solomon's
["In Bb 2.0"](https://www.inbflat.net/) (2009), after Terry
Riley's "In C" (1964). Twenty musicians - each a short video,
everyone playing in the key of B flat - wait in the wings of a
dark concert hall for your code to call them on. The code is
the score, and you are the conductor.

Press Play to hear it. Share it as a link. Read the
[docs](docs/) to get creative (there is a remarkable amount
you can do).

## Performing it locally

It is a static site: serve this directory over http and open
the page - for example `python -m http.server`, then visit
`http://localhost:8000/`. Opening `index.html` from the
filesystem is not enough, as the page fetches its Python
files and media over http.

## The rooms

The rehearsal room is the light page you arrive at: an editor
holding a score, and Play, Share and Docs. The concert hall
is the dark, full-screen room a performance happens in, with
its programme notes, its breathing light, and Stop. The
score's vocabulary - `arrange`, `enter`, `rest`, `crescendo`,
`tacet`, `followspot`, `keys` and the rest - is taught, with
live examples, in [the documentation](docs/).

## The repository

    index.html      the rooms (markup only)
    style.css       the light and the dark
    main.py         the bootstrap
    score.py        the default score
    inbflat.py      the stagehand (the score's vocabulary)
    verses.py       the poem, timed
    fonts/          Mebinac, the site's voice
    videos/         the ensemble, with SOURCES.txt
    examples/       scores to steal from
    docs/           the story of the vocabulary
    tools/          check_docs.py, the honesty rig

Sharing works with no server at all: the Share button puts
the whole score into the page's URL fragment, which never
leaves the browser - a performance simply is its link.

## The music and its makers

The twenty performances were recorded by their musicians for
Darren Solomon's "In Bb 2.0", whose
[FAQ](https://www.inbflat.net/faq.html) warmly invites
remixing; this project archives and replays them with credit
and gratitude. Every file's provenance - its YouTube source,
original title, and stage name - is recorded in
[videos/SOURCES.txt](videos/SOURCES.txt). One performer
speaks rather than plays: "Information", a poem written and
read by Daniel Donahoo. If any performer would like their
work amended or removed, say so and it will be done
promptly.

## Made with

[Browser Friendly Python](https://bfp.dev/) runs
[MicroPython](https://micropython.org/) in the page - no
JavaScript was written for this site. The editor is
[CodeMirror](https://codemirror.net/); the live documentation
examples run via
[importpython.org](https://importpython.org/); the poem's
timings were transcribed with
[Whisper](https://github.com/openai/whisper). The type is
Mebinac.

## Checks

    python tools/check_docs.py

verifies that every "play it on the stage" link in the
documentation carries exactly the score its neighbouring
code block displays, and that every such score compiles.
Run it after hand-editing the docs.

## Licence

The code and prose of this project are offered under the
terms in [LICENSE](LICENSE.md). The video and audio recordings
in `videos/` are the work of their performers and are not
covered by that licence: they are archived here under the
original project's remix invitation, credited in
`videos/SOURCES.txt`, and will be removed on request.