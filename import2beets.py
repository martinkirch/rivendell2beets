#!/usr/bin/env python3
"""

TODO:
https://github.com/beetbox/pyacoustid
or beets's acousticID plugin ?

howto force beet's import date ?


"""

# path to Rivendell sounds (defaults to /srv/rivendell/snd/)
RIVENDELL_SND = "/srv/rivendell/snd/"

# I advise you to convert everything to FLAC first, with a bash loop and ffmpeg (and even ffmpeg-normalize)
# but if you wan to use Rivendell sounds directly, set this to ".wav"
CUT_EXTENSION = ".flac"


from datetime import datetime
from collections import defaultdict
import sqlite3
import re

SHITTY_TITLE = re.compile(r"(\[new cart\])|(Untitled)|(Track\s+[0-9]+)", re.IGNORECASE)
TITLE_FIXER = re.compile(r"([A-Z]?[0-9]+)?([^\-]{3,}) - (.*)")

conn = sqlite3.connect('rivendell.db')
conn.row_factory = sqlite3.Row

schedcodes = set()

def pr(entry):
    print("{} {} - {} {} {}".format(
        entry["CUT_NAME"],
        entry["ARTIST"],
        entry["TITLE"],
        entry["SCHED_CODES"],
        entry["ORIGIN_DATETIME"],
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
    if not artist:
        m = TITLE_FIXER.match(title)
        if m:
            artist = m.group(2)
            title = m.group(3)
        else:
            pr(row)
    if SHITTY_TITLE.match(title):
        title = None
    # TODO check file CUT_NAME.wav exists


conn.close()
