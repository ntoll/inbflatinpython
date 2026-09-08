"""
InB♭InPython - after Darren Solomon's "In Bb 2.0", after Terry Riley's 
"In C".

This code is a musical score and you are the conductor: choose a seed,
arrange an orchestra, start the performance.

Press Play to hear it. Share it as a link. Read the Docs to get creative
(there is a remarkable amount you can do).
"""
import random
from inbflat import arrange, enter, rest, keys, start


random.seed(1935)  # The year Terry Riley was born.
orchestra = arrange(musicians=13, polyphony=5)


async def performance():
    """
    One by one the musicians enter, and then listen.
    """
    for musician in orchestra:
        await enter(musician)
        await rest(8, 16)
    keys()


start(performance())