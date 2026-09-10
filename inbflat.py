"""
inbflat: the fundamental code for InBflatInPython - a remix, in Python,
of Darren Solomon's "In Bb 2.0" (https://www.inbflat.net/), built on
Browser Friendly Python (https://bfp.dev).

The score created in the website imports from this module. Nothing here is
secret - it simply hides the browser plumbing so the score itself can read
like musical code.
"""
import asyncio
import random
from bfp import ffi, web, window
from verses import VERSES


# The twenty performers of "In Bb 2.0".
# Spaces become hyphens, so "plastic toy sax" plays
# videos/plastic-toy-sax.mp4 with videos/plastic-toy-sax.jpg
# as its poster. The provenance of every file, including its
# original YouTube source, is recorded in videos/SOURCES.txt.
MUSICIANS = [
    "electric guitar",
    "mallets",
    "kaoss pad",
    "acoustic violin",
    "plastic toy sax",
    "electric bass",
    "harmon trumpet",
    "clarinet",
    "vocals",
    "banjo with ebow",
    "the poem",  
    "ebow",
    "acoustic guitar",
    "balloons ambience",
    "omnichord and qchord",
    "korg ds-10",
    "synth cello",
    "emx-1",
    "acoustic piano",
    "rhodes keyboard",
]

# The sections, for scores that compose by family. These are
# ordinary lists: conductors are encouraged to create their
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

# Note letters to semitone steps, for the keys.
_PITCH = {"C": 0, "D": 2, "E": 4, "F": 5, "G": 7, "A": 9,
          "B": 11}

# The concert's state, reset by clear().
_concert = []       # Scheduled tasks, cancelled by clear().
_players = []       # The performers on stage.
_seats = None       # This concert's shuffled seating plan.
_polyphony = None   # Voice cap; None means unlimited.
_recital = False    # Whether the poem's words have begun.
_log_lines = []     # The most recent log entries.
_verse_cursor = 3   # Vertical % cursor for cascading words.
_caption_jitter = 0  # Scatter counter for caption().
_proclaim_slot = 0  # Which mid-stage slot proclaim() uses.
_audio = None       # Shared audio context for the keys.
_palette = []       # The keys' notes, for the number keys.


def _log(message):
    """
    Add `message` to the log in the menu bar. Only the
    most recent three entries are shown.
    """
    _log_lines.append(message)
    del _log_lines[:-3]
    web.page["log"].textContent = "   ".join(
        [">>> " + note for note in _log_lines]
    )


def _pulse(breathing):
    """
    Set the menu bar's light: `breathing` True animates it,
    False holds it dim and still.
    """
    pulse = web.page["pulse"]
    if breathing:
        pulse.classes.remove("still")
    else:
        pulse.classes.add("still")


def _shuffle(items):
    """
    Shuffle `items` in place, Fisher-Yates. MicroPython's
    random module has no shuffle of its own; building on
    random.randrange keeps the score's seed in charge.
    """
    for i in range(len(items) - 1, 0, -1):
        j = random.randrange(i + 1)
        items[i], items[j] = items[j], items[i]


def arrange(musicians=12, polyphony=None, featuring=None):
    """
    Arrange an orchestra and return it as a list of names.

    `musicians` is how many take part, chosen and ordered
    by the seeded shuffle; asking for more than exist
    invites the whole company. `polyphony`, if given, caps how many
    sound at once. `featuring`, if given, names a musician
    guaranteed a place at a random position in the order.
    """
    global _polyphony
    if polyphony is not None:
        _polyphony = max(1, int(polyphony))
    if featuring is not None and featuring not in MUSICIANS:
        raise ValueError(
            "No performer called " + repr(featuring) + "."
        )
    names = list(MUSICIANS)
    _shuffle(names)
    musicians = max(0, min(musicians, len(names)))
    company = names[:musicians]
    if featuring is not None and featuring not in company:
        if company:
            company[random.randrange(len(company))] = featuring
        else:
            company.append(featuring)
    return company


def polyphony(limit):
    """
    Cap how many musicians sound at once to `limit` (at
    least 1). Usually set when arranging; call it
    mid-performance to thin or thicken the texture.
    """
    global _polyphony
    _polyphony = max(1, int(limit))


def _ended_count():
    """How many entered performers have finished."""
    return len(
        [player for player in _players if player["ended"]]
    )


async def _free_voice():
    """
    Wait until the polyphony cap admits another voice.
    Returns at once when there is room or no cap is set.
    """
    if _polyphony is None:
        return
    while (len(_players) - _ended_count()) >= _polyphony:
        await asyncio.sleep(0.25)


async def rest(shortest=4, longest=None):
    """
    Rest for a while.

    One argument is exact seconds: rest(4). With two, a
    duration is picked uniformly between `shortest` and
    `longest`: rest(1, 7). When the polyphony is capped and every voice
    sounds, the rest first waits for a voice to fall silent,
    then counts its seconds - so the gap sits between an
    exit and the entrance that follows.
    """
    await _free_voice()
    if longest is None:
        duration = shortest
    else:
        duration = random.uniform(shortest, longest)
    await asyncio.sleep(max(0, duration))


def _media(name, kind):
    """
    Return the path of a musician's file in videos/: `name`
    with spaces as hyphens, plus the `kind` ("mp4" or
    "jpg").
    """
    return "videos/" + name.replace(" ", "-") + "." + kind


def _take_seat(seat):
    """
    Claim a seat and return its number.

    With `seat` None a random free seat is claimed, or
    None is returned for a full house. A named `seat` (0 to 19,
    left to right then top to bottom) is claimed exactly;
    a taken or unknown seat raises ValueError.
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


async def _reveal(figure):
    """Fade `figure` up once the browser has placed it."""
    await asyncio.sleep(0.05)
    figure.style["opacity"] = "1"


def _watch(video, player):
    """
    Wire `video`'s media events to `player`'s life on stage.

    A playing event logs the entrance, wakes the pulse and,
    for the poem, starts the recital. An ended event logs
    the exit and leaves the performer's ghost - the frame
    stays where it is until clear() sweeps the stage.
    bfp.web's event table
    does not yet cover media events, so the listeners attach
    via the _dom_element escape hatch.
    """
    def on_playing(event):
        """Log the entrance; the poem also starts reciting."""
        global _recital
        if player["started"]:
            return
        player["started"] = True
        _log(player["name"] + " starting")
        _pulse(True)
        if player["name"] == "the poem" and not _recital:
            _recital = True
            start(_recite_poem())

    def on_ended(event):
        """Log the exit; the video gives way to the ghost."""
        if player["ended"]:
            return
        player["ended"] = True
        _log(player["name"] + " stopping")
        # Any followspot dimming lifts with the exit, so
        # every ghost glows the same.
        player["figure"].style["opacity"] = "1"
        player["figure"].classes.add("ended")
        if _ended_count() == len(_players):
            _pulse(False)

    element = video._dom_element
    element.addEventListener(
        "playing", ffi.create_proxy(on_playing)
    )
    element.addEventListener(
        "ended", ffi.create_proxy(on_ended)
    )


async def enter(name, seat=None, dynamic=1):
    """
    Bring a musician on stage and start them sounding.

    `name` is the musician. `seat`, if given, places them
    exactly (0 to 19); otherwise a random free seat is
    chosen. `dynamic`
    is the level they begin at, 0 (silent) to 1 (full) -
    enter at 0 and crescendo for a composed fade-in. When
    the polyphony is capped, waits for a free voice first.
    """
    if name not in MUSICIANS:
        raise ValueError("No performer called " + repr(name) + ".")
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
    # The ghost: the performer's still, layered beneath the
    # video and revealed very dimly when their performance
    # ends. The browser already holds the jpg - it is the
    # poster.
    ghost = web.img(src=_media(name, "jpg"), alt="")
    ghost.classes.add("ghost")
    figure = web.figure(ghost)
    figure.append(video)
    figure.style["grid-column"] = str(seat % SEAT_COLUMNS + 1)
    figure.style["grid-row"] = str(seat // SEAT_COLUMNS + 1)
    figure.style["opacity"] = "0"
    player = {
        "name": name,
        "figure": figure,
        "video": video,
        "ghost": ghost,
        "media": video._dom_element,
        "started": False,
        "ended": False,
    }
    _players.append(player)
    _watch(video, player)
    web.page["stage"].append(figure)
    player["media"].volume = min(1, max(0, dynamic))
    player["media"].play()
    await _reveal(figure)


def _find(name):
    """
    Return the most recent player called `name`, or None. A
    musician who returns after a tacet appears twice; the
    latest appearance is the live one.
    """
    for player in reversed(_players):
        if player["name"] == name:
            return player
    return None


async def _glide_media(media, to, over):
    """
    Slide `media`'s volume to `to` over `over` seconds, in
    small steps. An `over` of 0 sets it at once.
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
    Glide the volume of the player called `name` to `to`
    over `over` seconds, logging the `marking`. Does nothing
    if they are absent or already silent.
    """
    player = _find(name)
    if player is None or player["ended"]:
        return
    _log(name + " " + marking)
    await _glide_media(player["media"], to, over)


async def crescendo(name, to=1.0, over=4):
    """Grow `name`'s volume to `to` over `over` seconds."""
    await _glide(name, to, over, "crescendo")


async def diminuendo(name, to=0.2, over=4):
    """Sink `name`'s volume to `to` over `over` seconds."""
    await _glide(name, to, over, "diminuendo")


async def tacet(name, niente=4):
    """
    Silence the musician called `name` where they sit.

    Sound fades to nothing and the video gives way to the
    performer's ghost over `niente` seconds; 0 is immediate.
    Their voice frees at once, so a
    waiting musician may cross-fade in, and they may enter()
    again later at a fresh seat.
    """
    player = _find(name)
    if player is None or player["ended"]:
        return
    player["ended"] = True
    _log(name + " tacet")
    duration = str(niente) + "s"
    player["video"].style["transition-duration"] = duration
    ghost = player["ghost"]
    ghost.style["transition-duration"] = duration
    ghost.style["transition-delay"] = duration
    # Any followspot dimming lifts with the exit, so every
    # ghost glows the same.
    player["figure"].style["opacity"] = "1"
    player["figure"].classes.add("ended")
    if niente > 0:
        await _glide_media(player["media"], 0, niente)
    player["media"].pause()
    if _ended_count() == len(_players):
        _pulse(False)


async def ensemble(*parts):
    """
    Perform several `parts` as one, returning when the last
    finishes: await ensemble(enter("clarinet"),
    enter("vocals")).
    """
    await asyncio.gather(*parts)


def followspot(name):
    """
    Light only the performer called `name` and dim the rest.
    Calling it again moves the light; wash() restores an
    even stage.
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
    """Return every sounding performer to full light."""
    _log("an even wash")
    for player in _players:
        if not player["ended"]:
            player["figure"].style["opacity"] = "1"


def _drift(jitter, span, step):
    """
    Return a deterministic value in [0, `span`).

    `jitter` is a counter and `step` a stride sharing no
    factor with `span`, so successive values scatter without
    a short cycle. Used instead of the random module so the
    words' look never spends the music's seeded stream.
    """
    return (jitter * step) % span


async def _cascade(text, jitter, hold):
    """
    Place a line of words on the stage.

    The `text` is displayed on the screen at a horizontal
    position and size determined by the `jitter` (fed into
    `_drift`) for `hold` many seconds. Vertical placement is
    decided via the `global _verse_cursor` that tracks the
    previous line's box.
    """
    global _verse_cursor
    verses = web.page["verses"]
    verse = web.p(text)
    verse.style["opacity"] = "0"
    left = 6 + _drift(jitter, 30, 37)
    size = 140 + _drift(jitter, 110, 53)
    verse.style["left"] = str(left) + "%"
    verse.style["font-size"] = str(size / 100) + "rem"
    if _verse_cursor > 82:
        _verse_cursor = 3
    verse.style["top"] = str(_verse_cursor) + "%"
    verses.append(verse)
    await asyncio.sleep(0.05)
    # Measure the rendered box and move the cursor past it,
    # so the next line cannot collide with this one.
    height = verse._dom_element.offsetHeight
    room = verses._dom_element.offsetHeight
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
    Place a line of words centred mid-stage.

    The `text` lands large at one of three heights chosen by
    `slot` (0 to 2), stays for `hold` seconds, then fades.
    Its box is as wide as the text needs, capped at 80% of
    the stage.
    """
    verses = web.page["verses"]
    verse = web.p(text)
    verse.style["opacity"] = "0"
    verse.style["top"] = str(36 + slot * 11) + "%"
    verse.style["left"] = "50%"
    verse.style["transform"] = "translateX(-50%)"
    verse.style["width"] = "max-content"
    verse.style["max-width"] = "80%"
    verse.style["text-align"] = "center"
    verse.style["font-size"] = "2.6rem"
    verses.append(verse)
    await asyncio.sleep(0.05)
    verse.style["opacity"] = "1"
    await asyncio.sleep(hold)
    verse.style["opacity"] = "0"


async def _show_verse(index, line):
    """
    Place phrase `index` of the poem, showing `line`. The
    final three phrases take the still treatment for 12
    seconds; the rest cascade for 7.
    """
    if index >= len(VERSES) - 3:
        await _still(line, index - (len(VERSES) - 3), 12)
    else:
        await _cascade(line, index, 7)


async def _recite_poem():
    """
    Speak the poem: each phrase of VERSES is scheduled at
    its recorded moment, timed from this coroutine's start.
    """
    elapsed = 0.0
    for index, (moment, line) in enumerate(VERSES):
        await asyncio.sleep(max(0, moment - elapsed))
        elapsed = moment
        start(_show_verse(index, line))


async def caption(text, hold=6):
    """
    Show one cascading line of `text` for `hold` seconds,
    placed clear of other lines.
    """
    global _caption_jitter
    _caption_jitter += 1
    await _cascade(text, _caption_jitter * 7 + 3, hold)


async def proclaim(text, hold=12):
    """
    Show `text` centred and large mid-stage for `hold`
    seconds - the treatment of the poem's close.
    """
    global _proclaim_slot
    slot = _proclaim_slot % 3
    _proclaim_slot += 1
    await _still(text, slot, hold)


async def _recite_lines(lines):
    """
    Deliver `lines` of (seconds, text) pairs, each as a
    caption at its moment, timed from this coroutine's
    start.
    """
    begun = 0.0
    for moment, text in lines:
        await asyncio.sleep(max(0, moment - begun))
        begun = moment
        start(caption(text))


def recite(lines):
    """
    Speak `lines` - a list of (seconds, text) pairs - timed
    from this call. Returns the scheduled task.
    """
    return start(_recite_lines(list(lines)))


def _frequency(note):
    """
    Return the frequency of `note`, named like "Bb3" or
    "F#4", tuned to A4 = 440.
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
    Sound one note through `audio`: an oscillator of the
    given `wave` at `frequency` rises to `peak` gain over
    `attack` seconds, then releases exponentially to nothing
    over `release` seconds.
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


# The built-in timbres, by name. A home-made timbre is a
# function of (audio, frequency) that makes a sound.
_TIMBRES = {
    "bell": _bell,
    "pluck": _pluck,
    "breath": _breath,
    "drone": _drone,
}


def _sound(frequency, timbre):
    """
    Sound `frequency` in the given `timbre` - a name from
    _TIMBRES or a function of (audio, frequency) - creating
    the shared audio context on first use (a key press is
    the gesture the browser wants).
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


def _strike_note(entry):
    """Sound the palette `entry`'s note and log its name."""
    _sound(entry["frequency"], entry["timbre"])
    _log(entry["label"])


async def _flash(key):
    """Light `key` briefly, so a typed digit reads as a press."""
    key.classes.add("struck")
    await asyncio.sleep(0.15)
    key.classes.remove("struck")


def _strike_digit(event):
    """
    Sound the key a typed digit points at: 1 to 9 are the
    first nine keys, 0 the tenth. Idle while the palette is
    empty (no keys() on stage), so typing digits in the
    rehearsal room stays just typing.
    """
    if not _palette or event.repeat:
        return
    if event.ctrlKey or event.altKey or event.metaKey:
        return
    place = "1234567890".find(event.key)
    if place < 0 or place >= len(_palette):
        return
    entry = _palette[place]
    _strike_note(entry)
    start(_flash(entry["key"]))


# The whole hall listens for the digits, so a keyboard
# player need not focus the on-screen row first.
window.document.addEventListener(
    "keydown", ffi.create_proxy(_strike_digit)
)


def keys(timbre="bell", notes=None):
    """
    Lay a row of keys along the foot of the stage.

    Each key sounds a note when pressed - by pointer, or by
    typing 1 to 9 and 0 for the tenth. The `timbre`
    chooses the voice: "bell", "pluck", "breath", "drone",
    or your own function of (audio, frequency). The `notes`,
    if given, set the palette - flats and sharps welcome,
    like ["Bb3", "F#4", "C5"] - and default to the B flat
    major pentatonic, so whatever is pressed belongs. Swept
    away, like everything, by Stop.
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
    del _palette[:]
    row = web.div(id="keys")
    for note in notes:
        frequency = _frequency(note)
        if len(note) > 1 and note[1] == "b":
            label = note[0] + "\u266d" + note[2:]
        elif len(note) > 1 and note[1] == "#":
            label = note[0] + "\u266f" + note[2:]
        else:
            label = note
        key = web.button(label)
        entry = {
            "label": label,
            "frequency": frequency,
            "timbre": timbre,
            "key": key,
        }
        _palette.append(entry)

        def strike(event, entry=entry):
            """Sound the note the instant the key goes down."""
            _strike_note(entry)

        def strike_key(event, entry=entry):
            """Sound on Enter or Space, once per press."""
            if event.repeat:
                return
            if event.key in ("Enter", " "):
                event.preventDefault()
                _strike_note(entry)

        # An instrument sounds on the way down, not on
        # release, so keys bind pointerdown rather than
        # click - with keydown alongside for keyboard
        # players.
        key._dom_element.addEventListener(
            "pointerdown", ffi.create_proxy(strike)
        )
        key._dom_element.addEventListener(
            "keydown", ffi.create_proxy(strike_key)
        )
        row.append(key)
    web.page["boards"].append(row)
    _log("keys ready, click to play or type 0-9")


def prop(element, seat=None):
    """
    Seat any `element` on stage as a prop.

    `seat`, if given, places it exactly (0 to 19);
    otherwise a random free seat is chosen. Returns the
    figure holding it, or None for a full house. Props
    take seats but not voices: the polyphony ignores
    them.
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
    Schedule the `performance` coroutine and remember its
    task so clear() can cancel it. Returns the task. The
    score calls this once with the whole piece; the
    stagehand uses it for every fade and verse, so Stop
    silences everything at once.
    """
    task = asyncio.create_task(performance)
    _concert.append(task)
    return task


def clear():
    """
    Stop everything and empty the stage: cancel every task,
    remove the players, the words and the keys, and reset
    the concert's state.
    """
    global _seats, _polyphony, _recital, _verse_cursor
    global _caption_jitter, _proclaim_slot
    while _concert:
        _concert.pop().cancel()
    for area in ("stage", "verses", "log"):
        web.page[area].innerHTML = ""
    row = web.page["keys"]
    if row is not None:
        row._dom_element.remove()
    del _players[:]
    del _palette[:]
    del _log_lines[:]
    _seats = None
    _polyphony = None
    _recital = False
    _verse_cursor = 3
    _caption_jitter = 0
    _proclaim_slot = 0
    _pulse(True)