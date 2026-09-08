"""
inbflat: the stagehand for InB♭InPython - a remix, in Python,
of Darren Solomon's "In Bb 2.0" (https://www.inbflat.net/),
built on Browser Friendly Python.

The visible score imports from this module. Nothing here is
secret - it simply hides the browser plumbing so the score
itself can read like music.
"""
import asyncio
import random
from bfp import ffi, web, window
from verses import VERSES

# The twenty performers of "In Bb 2.0", in stage order. A
# simple convention maps each name to their media: spaces
# become hyphens, so "plastic toy sax" plays
# videos/plastic-toy-sax.mp4 with videos/plastic-toy-sax.jpg
# as its poster. The provenance of every file, including its
# original YouTube source, is recorded in videos/urls.txt.
MUSICIANS = [
    "mallets",
    "electric guitar",
    "kaoss pad",
    "rhodes keyboard",
    "plastic toy sax",
    "electric bass",
    "harmon trumpet",
    "clarinet",
    "vocals",
    "banjo with ebow",
    "the poem",
    "korg ds-10",
    "acoustic guitar",
    "balloons ambience",
    "omnichord and qchord",
    "ebow",
    "synth cello",
    "emx-1",
    "acoustic piano",
    "acoustic violin",
]


# The company by name, in stage order, for scores that want
# to choose from the whole ensemble.
performers = list(MUSICIANS)

# The sections, for scores that compose by family. These are
# ordinary lists: conductors are encouraged to cast their
# own - by mood, by texture, by whatever the piece wants.
strings = [
    "electric guitar",
    "acoustic guitar",
    "electric bass",
    "banjo with ebow",
    "ebow",
    "acoustic violin",
    "synth cello",
]
winds = ["harmon trumpet", "clarinet", "plastic toy sax"]
keyboards = ["rhodes keyboard", "acoustic piano"]
electronics = [
    "kaoss pad",
    "korg ds-10",
    "emx-1",
    "omnichord and qchord",
    "balloons ambience",
]
percussion = ["mallets"]
voices = ["vocals", "the poem"]

# The stage plan: five seats across, four deep, matching the
# CSS grid. Twenty seats for twenty performers.
SEAT_COLUMNS = 5
SEAT_ROWS = 4

# Mutable state for the current evening, reset by clear().
_performance = []  # Scheduled tasks, cancelled by clear().
_players = []      # The performers on stage this evening.
_seats = None      # This evening's shuffled seating plan.
_recital = False   # Whether the poem's words have begun.
_log_lines = []    # The most recent programme notes.
_verse_cursor = 3  # Vertical %% cursor for verse placing.
_voices = None     # Polyphony cap; None means unlimited.


def _log(message):
    """
    Add a line to the programme notes in the menu bar,
    keeping only the most recent few in view.
    """
    _log_lines.append(message)
    del _log_lines[:-3]
    area = web.page["log"]
    if area is not None:
        area.textContent = "   ".join(
            [">>> " + note for note in _log_lines]
        )


def _shuffle(items):
    """
    Fisher-Yates, in place. MicroPython's random module has
    no shuffle of its own, so the stagehand carries one. It
    is built on random.randrange, so the score's random.seed
    governs it.
    """
    for i in range(len(items) - 1, 0, -1):
        j = random.randrange(i + 1)
        items[i], items[j] = items[j], items[i]


def arrange(musicians=12, polyphony=None, featuring=None):
    """
    Arrange an orchestra: how many musicians take part, in
    the entry order the seeded dice decide. polyphony caps
    how many sound at once - later musicians wait in the
    wings until a voice falls silent. Naming a performer via
    featuring guarantees them a place, though the dice still
    choose when they enter. Asking for more musicians than
    exist simply invites the whole company.
    """
    if polyphony is not None:
        _set_polyphony(polyphony)
    if featuring is not None and featuring not in MUSICIANS:
        raise ValueError(
            "No performer called " + repr(featuring) + "."
        )
    names = list(performers)
    _shuffle(names)
    musicians = max(0, min(musicians, len(names)))
    company = names[:musicians]
    if featuring is not None and featuring not in company:
        if company:
            company[random.randrange(len(company))] = featuring
        else:
            company.append(featuring)
    return company


async def rest(shortest=4, longest=None):
    """
    A musical rest. rest(4) is four seconds of patience;
    rest(1, 7) lets the seeded dice pick somewhere between
    one and seven seconds; a bare rest() is four seconds.
    When the polyphony is capped and every voice is
    sounding, a rest first listens until one falls silent
    and only then counts its seconds - so the gap the
    conductor wrote always sits between an exit and the
    entrance that follows.

    Rests are the silence where the music happens.
    """
    await _free_voice()
    if longest is None:
        duration = shortest
    else:
        duration = random.uniform(shortest, longest)
    await asyncio.sleep(max(0, duration))


def _pulse(breathing):
    """
    Set the menu bar's breathing light: alive while voices
    still sound, still once the final performer has stopped.
    """
    light = web.page["pulse"]
    if light is None:
        return
    if breathing:
        light.classes.remove("still")
    else:
        light.classes.add("still")


def _ended_count():
    """How many entered performers have finished."""
    total = 0
    for player in _players:
        if player["ended"]:
            total += 1
    return total


def _set_polyphony(limit):
    """Record the polyphony cap after gentle validation."""
    global _voices
    _voices = max(1, int(limit))


def polyphony(limit):
    """
    Cap how many musicians sound at once. Usually set when
    the orchestra is arranged, but a conductor may change it
    mid-performance to thin or thicken the texture.
    """
    _set_polyphony(limit)


async def _free_voice():
    """
    Wait in the wings until the polyphony cap admits another
    voice. Returns at once when the stage has room or no cap
    is set.
    """
    if _voices is None:
        return
    while (len(_players) - _ended_count()) >= _voices:
        await asyncio.sleep(0.25)


def _drift(index, span, step):
    """
    A deterministic value in [0, span) derived from an index.
    The poem's typography should look chance-led, but the
    seeded random stream belongs to the music, and the
    recital runs concurrently with it - drawing on the same
    stream would make the rests unrepeatable. Arithmetic
    stands in for the dice.
    """
    return (index * step) % span


async def _cascade(text, jitter, hold):
    """
    One line of words on the stage: placed at the measured
    cursor so lines never collide, drifting horizontally and
    sized by deterministic chance, fading after its hold.
    The shared engine beneath the poem's verses and the
    conductor's captions.
    """
    global _verse_cursor
    board = web.page["verses"]
    if board is None:
        return
    verse = web.p(text)
    verse.style["opacity"] = "0"
    left = 6 + _drift(jitter, 30, 37)
    size = 140 + _drift(jitter, 110, 53)
    verse.style["left"] = str(left) + "%"
    verse.style["font-size"] = str(size / 100) + "rem"
    if _verse_cursor > 82:
        _verse_cursor = 3
    verse.style["top"] = str(_verse_cursor) + "%"
    board.append(verse)
    await asyncio.sleep(0.05)
    # Measure the rendered box and advance the cursor past
    # it, so the next line cannot collide with this one.
    height = verse._dom_element.offsetHeight
    room = board._dom_element.offsetHeight
    if room:
        occupied = height * 100 / room
        if _verse_cursor + occupied > 97:
            _verse_cursor = 3
            verse.style["top"] = "3%"
        _verse_cursor = _verse_cursor + occupied + 2
    verse.style["opacity"] = "1"
    await asyncio.sleep(hold)
    verse.style["opacity"] = "0"


async def _still(text, slot, hold):
    """
    The still treatment: a line lands centred and large at
    one of three mid-stage places, over whatever remains,
    then fades after its hold. The poem's close and the
    conductor's proclamations share it.
    """
    board = web.page["verses"]
    if board is None:
        return
    verse = web.p(text)
    verse.style["opacity"] = "0"
    verse.style["top"] = str(36 + slot * 11) + "%"
    # The box hugs its words: as wide as the text asks, no
    # wider than the stage allows, centred by translation.
    verse.style["left"] = "50%"
    verse.style["transform"] = "translateX(-50%)"
    verse.style["width"] = "max-content"
    verse.style["max-width"] = "80%"
    verse.style["text-align"] = "center"
    verse.style["font-size"] = "2.6rem"
    board.append(verse)
    await asyncio.sleep(0.05)
    verse.style["opacity"] = "1"
    await asyncio.sleep(hold)
    verse.style["opacity"] = "0"


async def _show_verse(index, line):
    """
    Place one phrase of the poem: the final three phrases -
    the close - take the still treatment and hold twelve
    seconds; the rest cascade.
    """
    if index >= len(VERSES) - 3:
        await _still(line, index - (len(VERSES) - 3), 12)
    else:
        await _cascade(line, index, 7)


async def _recite():
    """
    Speak the poem on the stage: each line is scheduled at
    its moment, timed from the instant the poem's player
    reports that it is playing.
    """
    elapsed = 0.0
    for index, (moment, line) in enumerate(VERSES):
        await asyncio.sleep(max(0, moment - elapsed))
        elapsed = moment
        start(_show_verse(index, line))


def _media(name, kind):
    """
    The path convention: a performer's name, spaces as
    hyphens, finds their video ("mp4") or poster ("jpg")
    in the videos directory.
    """
    return "videos/" + name.replace(" ", "-") + "." + kind


def _begin_recital():
    """Start the poem's words, once, from its first sound."""
    global _recital
    if not _recital:
        _recital = True
        start(_recite())


def _watch(video, player):
    """
    Wire a performer's own media events. Native video tells
    us honestly when it starts and finishes - the very
    things a YouTube iframe once made us reconstruct from
    postMessage reports. bfp.web's event table does not yet
    cover media events, so the listeners attach through the
    documented _dom_element escape hatch.
    """
    def on_playing(event):
        """Log the entrance; the poem also begins reciting."""
        if player["started"]:
            return
        player["started"] = True
        _log(player["name"] + " starting")
        _pulse(True)
        if player["name"] == "the poem":
            _begin_recital()

    def on_ended(event):
        """Log the exit; the fade is the exit itself."""
        if player["ended"]:
            return
        player["ended"] = True
        _log(player["name"] + " stopping")
        # The faded frame rests where it is until clear()
        # sweeps the stage between performances.
        player["figure"].style["opacity"] = "0"
        if _ended_count() == len(_players):
            _pulse(False)

    element = video._dom_element
    element.addEventListener(
        "playing", ffi.create_proxy(on_playing)
    )
    element.addEventListener(
        "ended", ffi.create_proxy(on_ended)
    )


def _take_seat(seat):
    """
    Claim a seat. The dice pick a free one when none is
    named; a named seat (0 to 19, left to right then top to
    bottom) is claimed exactly, if it is still free. Returns
    None for a full house.
    """
    global _seats
    if _seats is None:
        _seats = list(range(SEAT_COLUMNS * SEAT_ROWS))
        _shuffle(_seats)
    if seat is None:
        if not _seats:
            return None
        return _seats.pop()
    if seat not in _seats:
        raise ValueError(
            "Seat " + str(seat)
            + " is not free (seats are 0 to 19)."
        )
    _seats.remove(seat)
    return seat


async def enter(name, seat=None, dynamic=1):
    """
    Bring a performer on stage - to a seat the dice choose,
    or to a named seat (0 to 19) so a conductor can arrange
    the layout of the band - start their video sounding
    (pressing Play was the gesture that permits it), and
    fade them in. The dynamic sets the level they begin at,
    from 0 (silent) to 1 (full): enter someone at 0 and
    crescendo them, and you have composed a fade-in.
    """
    if name not in MUSICIANS:
        raise ValueError("No performer called " + repr(name) + ".")
    # A backstop for scores that enter without resting:
    # never exceed the cap. A score whose rests carry the
    # waiting (the usual shape) never blocks here.
    await _free_voice()
    seat = _take_seat(seat)
    if seat is None:
        return
    video = web.video(
        src=_media(name, "mp4"),
        poster=_media(name, "jpg"),
        playsinline="",
        title=name,
    )
    figure = web.figure(video)
    figure.style["grid-column"] = str(seat % SEAT_COLUMNS + 1)
    figure.style["grid-row"] = str(seat // SEAT_COLUMNS + 1)
    figure.style["opacity"] = "0"
    player = {
        "name": name,
        "figure": figure,
        "media": video._dom_element,
        "started": False,
        "ended": False,
    }
    _players.append(player)
    _watch(video, player)
    web.page["stage"].append(figure)
    player["media"].volume = min(1, max(0, dynamic))
    player["media"].play()
    await asyncio.sleep(0.05)
    figure.style["opacity"] = "1"


def _find(name):
    """
    The most recent appearance of a named performer, since a
    musician who returns after a tacet appears twice.
    """
    for player in reversed(_players):
        if player["name"] == name:
            return player
    return None


async def _glide_media(media, to, over):
    """
    Slide a media element's volume to a target over some
    seconds: the engine beneath crescendo, diminuendo and
    tacet's niente.
    """
    to = min(1.0, max(0.0, to))
    if over <= 0:
        media.volume = to
        return
    begin = media.volume
    steps = max(1, int(over * 20))
    for step in range(1, steps + 1):
        media.volume = begin + (to - begin) * step / steps
        await asyncio.sleep(over / steps)


async def _glide(name, to, over, marking):
    """
    Slide a named performer's volume to a target over some
    seconds, if they are still sounding, noting the marking
    in the programme.
    """
    player = _find(name)
    if player is None or player["ended"]:
        return
    _log(name + " " + marking)
    await _glide_media(player["media"], to, over)


async def crescendo(name, to=1.0, over=4):
    """
    Grow a performer's volume towards the target, over the
    given seconds. The other half of diminuendo.
    """
    await _glide(name, to, over, "crescendo")


async def diminuendo(name, to=0.2, over=4):
    """
    Sink a performer's volume towards the target, over the
    given seconds. The other half of crescendo.
    """
    await _glide(name, to, over, "diminuendo")


async def ensemble(*parts):
    """
    Perform several things as one - most often simultaneous
    entrances: await ensemble(enter("clarinet"),
    enter("vocals")). Returns when every part has.
    """
    await asyncio.gather(*parts)


async def tacet(name, niente=4):
    """
    The performer falls silent where they sit - tacet, as
    the part on the stand says. By default the silence
    arrives al niente: sound and light fade to nothing
    together over the given seconds, while 0 makes the
    silence immediate. Their voice returns to the wings at
    once (so a waiting musician may cross-fade in), and
    they may enter() again later at a fresh seat.
    """
    player = _find(name)
    if player is None or player["ended"]:
        return
    player["ended"] = True
    _log(name + " tacet")
    figure = player["figure"]
    figure.style["transition-duration"] = str(niente) + "s"
    figure.style["opacity"] = "0"
    if niente > 0:
        await _glide_media(player["media"], 0, niente)
    player["media"].pause()
    if _ended_count() == len(_players):
        _pulse(False)


def followspot(name):
    """
    Pick one performer out with the followspot: they hold
    full brightness while the rest of the stage dims down.
    Calling it on another performer moves the light; wash()
    restores an even stage.
    """
    _log("followspot on " + name)
    for player in _players:
        if player["ended"]:
            continue
        lit = player["name"] == name
        player["figure"].style["opacity"] = (
            "1" if lit else "0.35"
        )


def wash():
    """
    An even wash across the stage: every sounding performer
    returns to full light and nobody is special.
    """
    _log("an even wash")
    for player in _players:
        if not player["ended"]:
            player["figure"].style["opacity"] = "1"


# Jitter and slot counters for the conductor's own words,
# kept apart from the poem's so neither disturbs the other.
_caption_index = 0
_proclaim_slot = 0


async def caption(text, hold=6):
    """
    One line of the conductor's own words, given the poem's
    cascading treatment: it lands clear of other lines,
    holds, and fades. For a timed sequence see recite(); for
    the big centred treatment see proclaim().
    """
    global _caption_index
    _caption_index += 1
    await _cascade(text, _caption_index * 7 + 3, hold)


async def proclaim(text, hold=12):
    """
    Words with the weight of the poem's close: centred,
    large, mid-stage, over whatever remains, fading after
    the hold.
    """
    global _proclaim_slot
    slot = _proclaim_slot % 3
    _proclaim_slot += 1
    await _still(text, slot, hold)


async def _speak(lines):
    """
    Deliver (seconds, text) pairs from the moment of
    scheduling, each line as a caption.
    """
    begun = 0.0
    for moment, text in lines:
        await asyncio.sleep(max(0, moment - begun))
        begun = moment
        start(caption(text))


def recite(lines):
    """
    Speak a timed sequence of the conductor's words: lines
    is a list of (seconds, text) pairs, timed from this
    call - the machinery the poem itself uses. Returns the
    scheduled task.
    """
    return start(_speak(list(lines)))


# Note letters to semitone steps, for the keys.
_PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9,
          "B": 11}

# The shared audio context for the keys, created on the
# first press (a click is the gesture the browser wants).
_audio = None


def _frequency(note):
    """
    The frequency of a note named like "Bb3" or "F4", via
    its MIDI number, tuned to A4 = 440.
    """
    step = _PITCH.get(note[0].upper())
    if step is None:
        raise ValueError(
            "No note called " + repr(note)
            + " (notes look like 'Bb3', 'F#4' or 'C5')."
        )
    rest = note[1:]
    if rest.startswith("b"):
        step -= 1
        rest = rest[1:]
    elif rest.startswith("#"):
        step += 1
        rest = rest[1:]
    midi = (int(rest) + 1) * 12 + step
    return 440 * 2 ** ((midi - 69) / 12)


def _envelope(audio, frequency, wave, attack, peak, release):
    """
    One note: an oscillator of the given wave shaped by an
    attack to its peak and an exponential release to
    nothing. The engine beneath every built-in timbre.
    """
    now = audio.currentTime
    tone = audio.createOscillator()
    tone.type = wave
    tone.frequency.value = frequency
    level = audio.createGain()
    level.gain.setValueAtTime(0, now)
    level.gain.linearRampToValueAtTime(peak, now + attack)
    level.gain.exponentialRampToValueAtTime(
        0.001, now + attack + release
    )
    tone.connect(level)
    level.connect(audio.destination)
    tone.start(now)
    tone.stop(now + attack + release + 0.1)


def _bell(audio, frequency):
    """A soft bell: quick to speak, long to shimmer."""
    _envelope(audio, frequency, "sine", 0.02, 0.22, 2)


def _pluck(audio, frequency):
    """A plucked string: sharp start, quick decay."""
    _envelope(audio, frequency, "triangle", 0.005, 0.3, 0.5)


def _breath(audio, frequency):
    """A breathy swell: slow to speak, gentle to leave."""
    _envelope(audio, frequency, "sine", 0.3, 0.18, 1.6)


def _drone(audio, frequency):
    """A patient drone: slow bloom, very long fade."""
    _envelope(audio, frequency, "triangle", 0.6, 0.16, 6)


# The built-in timbres, by name. A home-made timbre is just
# a function of (audio, frequency) that makes a sound.
_TIMBRES = {
    "bell": _bell,
    "pluck": _pluck,
    "breath": _breath,
    "drone": _drone,
}


def _sound(frequency, timbre):
    """
    Sound one note of the chosen timbre, creating the
    shared audio context on first press (a click is the
    gesture the browser wants).
    """
    global _audio
    if _audio is None:
        _audio = window.AudioContext.new()
    if callable(timbre):
        voice = timbre
    else:
        voice = _TIMBRES.get(timbre)
    if voice is None:
        raise ValueError("No timbre called " + repr(timbre) + ".")
    voice(_audio, frequency)


def keys(timbre="bell", notes=None):
    """
    Lay the audience's keys along the foot of the stage:
    soft round buttons, each sounding a note of the B flat
    major pentatonic, so whatever is pressed belongs to the
    piece - the original's promise, moved to the audience's
    fingertips. The timbre chooses the voice - keys("pluck")
    - from "bell" (the default), "pluck", "breath" and
    "drone", or your own function of (audio, frequency)
    that makes a sound, which is how instruments are born.
    Pass notes for a different palette: flats and sharps
    both welcome, like ["Bb3", "F#4", "C5"]. Swept away,
    like everything, by Stop.
    """
    if isinstance(timbre, (list, tuple)):
        raise ValueError(
            "The first argument is the timbre; pass the"
            " palette as notes=[...]."
        )
    if notes is None:
        notes = ["Bb3", "C4", "D4", "F4", "G4", "Bb4"]
    old = web.page["keys"]
    if old is not None:
        old._dom_element.remove()
    row = web.div(id="keys")
    for note in notes:
        frequency = _frequency(note)
        if len(note) > 1 and note[1] == "b":
            label = note[0] + "\u266d" + note[2:]
        elif len(note) > 1 and note[1] == "#":
            label = note[0] + "\u266f" + note[2:]
        else:
            label = note

        def strike(event, frequency=frequency):
            """Sound the note the instant the key goes down."""
            _sound(frequency, timbre)

        def strike_key(event, frequency=frequency):
            """Sound on Enter or Space, once per press."""
            if event.repeat:
                return
            if event.key in ("Enter", " "):
                event.preventDefault()
                _sound(frequency, timbre)

        # An instrument sounds on the way down, not on
        # release, so these keys bind pointerdown rather
        # than click - with keydown alongside, since click
        # was also what let keyboard players play.
        key = web.button(label)
        key._dom_element.addEventListener(
            "pointerdown", ffi.create_proxy(strike)
        )
        key._dom_element.addEventListener(
            "keydown", ffi.create_proxy(strike_key)
        )
        row.append(key)
    web.page["boards"].append(row)


async def _reveal(figure):
    """Fade a newly placed figure up once it has landed."""
    await asyncio.sleep(0.05)
    figure.style["opacity"] = "1"


def prop(element, seat=None):
    """
    Place any element on stage as a prop, seated like a
    performer and fitted gracefully within its seat's
    bounds. With no seat given the dice pick a free one; a
    seat number (0 to 19, left to right, top to bottom)
    places it exactly, if free. Returns the figure holding
    it, for further styling. Props take seats but not
    voices: the polyphony ignores them.
    """
    seat = _take_seat(seat)
    if seat is None:
        return None
    figure = web.figure(element)
    figure.style["grid-column"] = str(seat % SEAT_COLUMNS + 1)
    figure.style["grid-row"] = str(seat // SEAT_COLUMNS + 1)
    figure.style["opacity"] = "0"
    web.page["stage"].append(figure)
    start(_reveal(figure))
    return figure


def start(performance):
    """
    Start a performance: schedule its coroutine as part of
    the evening, and remember the task so clear() can cancel
    it. The score calls this once with the whole piece; the
    stagehand also uses it for every fade and verse, so Stop
    silences everything at once.
    """
    task = asyncio.create_task(performance)
    _performance.append(task)
    return task


def clear():
    """
    Silence and an empty stage: cancel every scheduled task,
    remove the performers and the poem's words, and reset
    the evening's state.
    """
    global _seats, _recital, _verse_cursor, _voices
    global _caption_index, _proclaim_slot
    while _performance:
        _performance.pop().cancel()
    for area in ("stage", "verses", "log"):
        element = web.page[area]
        if element is not None:
            element.innerHTML = ""
    row = web.page["keys"]
    if row is not None:
        row._dom_element.remove()
    del _players[:]
    del _log_lines[:]
    _seats = None
    _recital = False
    _verse_cursor = 3
    _caption_index = 0
    _proclaim_slot = 0
    _voices = None
    _pulse(True)