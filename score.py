"""
InB♭InPython - after Darren Solomon's "In Bb 2.0", after Terry Riley's 
"In C". Poetry by Daniel Donahoo. The About page tells you more.

This code is a musical score and you are the conductor: choose a seed
(starting state), arrange an orchestra, start the performance.

Press Play to hear it. Share it as a link. Read the Docs to get creative
(there is a remarkable amount you can do - have fun!).
"""
import random
from inbflat import arrange, enter, rest, keys, start


random.seed(1935)  # The year Terry Riley was born.
# An orchestra of 13 musicians, but only 5 concurrent players at once.
orchestra = arrange(musicians=13, polyphony=5)


async def performance():
    """
    One by one the musicians enter, and then rest.
    """
    for musician in orchestra:  # it's a loop, what more can I say?
        await enter(musician)  # wait for a musician to enter the stage.
        await rest(8, 16)  # rest 8-16 seconds before the next entry.
    keys()  # at the end, show keys to play your own notes. ;-)


start(performance())  # Go! Enjoy and share the music. 🐍❤️🎵📡🤗