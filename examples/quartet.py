"""
A string quartet, through-composed: no dice, every entrance
written. Paste into the editor and press Play - then change
everything.
"""
from inbflat import (caption, crescendo, diminuendo, enter,
                     ensemble, followspot, rest, start, tacet,
                     wash)


async def performance():
    """Four strings, one followspot, a quiet ending."""
    await ensemble(
        enter("acoustic violin"),
        enter("synth cello"),
    )
    await rest(10)
    await ensemble(
        enter("acoustic guitar"),
        enter("electric bass"),
    )
    await rest(8)
    followspot("acoustic violin")
    await crescendo("acoustic violin", to=1.0, over=6)
    await rest(12)
    wash()
    await diminuendo("synth cello", to=0.3, over=8)
    await rest(8)
    await tacet("electric bass")
    await rest(6)
    await tacet("acoustic guitar")
    await caption("and then, quietly, the strings alone")
    await rest(10)
    await ensemble(
        tacet("synth cello"),
        tacet("acoustic violin"),
    )


start(performance())