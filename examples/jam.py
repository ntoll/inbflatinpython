"""
A jam for the audience: three long drones and a row of
keys. Whatever you press belongs. Press Play, then play.
"""
from inbflat import caption, enter, keys, rest, start


async def performance():
    """Drones settle, keys appear, the audience joins in."""
    await enter("ebow")
    await rest(6)
    await enter("balloons ambience")
    await rest(6)
    await enter("omnichord and qchord")
    await rest(4)
    keys()
    await caption("the keys are yours - press one", hold=10)


start(performance())