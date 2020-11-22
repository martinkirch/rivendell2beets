#!/usr/bin/env python3
"""
The trick is to load a Rivendell DB dump to Sqlite with:

./mysql2sqlite database-20201118-0625.sql | sqlite3 rivendell.db

Then set the constants below, and launch the script

TODO:
https://github.com/beetbox/pyacoustid
or beets's acousticID plugin ?

howto force beet's import date ?


"""

# path to Rivendell sounds
RIVENDELL_SND = "/srv/rivendell/snd/"

# I advise you to convert everything to FLAC first, with a bash loop and ffmpeg (and even ffmpeg-normalize)
# but if you wan to use Rivendell sounds directly:
CUT_EXTENSION = ".wav"


"""
select count(*) from CART where GROUP_NAME='MUSIC';
13485

1816 avec des tags pourris...

{'MuCntryBlu', 'Mu20142015', 'MuExtreme', 'MuLong', 'MuFR', 'MuElectro', 'MuRock',
'MuFolk', 'Mu20152016', 'MuMathPost', 'MuBassMsic', 'MuReprise', 'MuHouse', 'MuPop',
'MuSTAR2014', 'MuIndie', 'MuWorldLat', 'MuGOLD', 'MuPlayList', 'MuFunkSoul', 'MuPunk',
'MuChanson', 'MuJazz', 'Poesie', 'MuAmbient', 'MuHipHop', 'MuNoise', 'MuMetal',
'MuClassic', 'MuReggDub', 'MuExp', 'Poésie', 'MuRap', 'Nuit', 'MuTechno', 'MuCourt',
'MuDwnTempo', '.', 'MuLocal', 'MuGroovRnB', 'MuMoins1An', 'MuInstru', 'Creation'}

Top-10 artists:
[('Various Artists', 28), ('Shannon Wright', 22), ('Emily Jane White', 22), ('Do Make Say Think', 20), ('Jason Kahn', 18), ('Deerhoof', 17), ('Elysian Fields', 17), ('Sleaford Mods', 17), ('Stars Of The Lid', 16), ('Tim Hecker', 16)]
Top-10 titles:
[('S/t', 9), ('Lost', 5), ('Dawn', 4), ('Mirage', 4), ('Animal', 4), ('Downtown', 4), ('Kids', 4), ('Sunday Morning', 4), ('War', 4), ('Break', 4)]


"""
from datetime import datetime
from collections import defaultdict
import sqlite3
import re

SHITTY_TITLE = re.compile("(\[new cart\])|(Untitled)|(Track\s+[0-9]+)", re.IGNORECASE)
TITLE_FIXER = re.compile("([A-Z]?[0-9]+)?([^\-]{3,}) - (.*)")

conn = sqlite3.connect('rivendell.db')
conn.row_factory = sqlite3.Row

artist_count = defaultdict(int)
title_count = defaultdict(int)
schedcodes = set()

def pr(row):
    print("{} {} - {} {} {}".format(
        row["CUT_NAME"],
        row["ARTIST"],
        row["TITLE"],
        row["SCHED_CODES"],
        row["ORIGIN_DATETIME"],
    ))

for row in conn.execute("""
SELECT 
ARTIST, TITLE, SCHED_CODES,
CUT_NAME, ORIGIN_DATETIME
FROM CART c
JOIN CUTS cut ON CART_NUMBER = NUMBER
WHERE GROUP_NAME='MUSIC'
"""):
    try:
        origin = row['ORIGIN_DATETIME']
        if origin is None:
            pr(row)
        else:
            imported = datetime.fromisoformat(origin)
    except TypeError:
        print("cannot parse {!r}".format(origin))
    if row["SCHED_CODES"] is None:
        pr(row)
    else:
        for code in row["SCHED_CODES"].split(" "):
            if code:
                schedcodes.add(code)
    artist = row["ARTIST"]
    title = row["TITLE"]
    if artist:
        artist_count[artist] += 1
    else:
        m = TITLE_FIXER.match(title)
        if m:
            #print("can be save to {} // {}".format(m.group(2), m.group(3)))
            pass
        else:
            pr(row)
    if SHITTY_TITLE.match(title):
        pr(row)
    else:
        title_count[title] += 1
    # TODO check file CUT_NAME.wav exists




# print("scheduler codes:")
# print(schedcodes)

# artists = list(artist_count.items())
# artists.sort(key=lambda t: t[1], reverse=True)
# print("Top-10 artists:")
# print(artists[0:10])

# titles = list(title_count.items())
# titles.sort(key=lambda t: t[1], reverse=True)
# print("Top-10 titles:")
# print(titles[0:10])


conn.close()
