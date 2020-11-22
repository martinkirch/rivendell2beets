#!/usr/bin/env python3
"""

TODO:
howto force beet's import date ?
scheduler codes mapping

"""
from datetime import datetime
from collections import defaultdict
import re, os, sys, sqlite3, acoustid

# path to Rivendell sounds (defaults to /srv/rivendell/snd/)
# do not forget the trailing slash !
RIVENDELL_SND = "/srv/rivendell/snd/"

# I advise you to convert everything to FLAC first, with a bash loop and ffmpeg (and even ffmpeg-normalize)
# but if you wan to use Rivendell sounds directly, set this to ".wav"
CUT_EXTENSION = ".flac"

try:
    ACOUSTID_KEY = os.environ['ACOUSTID_KEY']
    if not ACOUSTID_KEY:
        raise KeyError()
except KeyError:
    print("please set ACOUSTID_KEY environment variable")
    sys.exit(1)


SHITTY_TITLE = re.compile(r"(\[new cart\])|(Untitled)|(Track\s+[0-9]+)", re.IGNORECASE)
TITLE_FIXER = re.compile(r"([A-Z]?[0-9]+)?([^\-]{3,}) - (.*)")

conn = sqlite3.connect('rivendell.db')
conn.row_factory = sqlite3.Row

schedcodes = set()

def pr(entry, prefix=''):
    print("{}{} {} - {} {} {}".format(
        prefix,
        entry["CUT_NAME"],
        entry["ARTIST"],
        entry["TITLE"],
        entry["SCHED_CODES"],
        entry["ORIGIN_DATETIME"],
    ))

IDENTIFIED_VIA_ACOUSTID = 0
SEEN = 0
IMPORTED = 0
REJECTED = 0

for row in conn.execute("""
SELECT 
ARTIST, TITLE, SCHED_CODES,
CUT_NAME, ORIGIN_DATETIME
FROM CART c
JOIN CUTS cut ON CART_NUMBER = NUMBER
WHERE GROUP_NAME='MUSIC'
"""):
    imported = None
    try:
        origin = row['ORIGIN_DATETIME']
        if origin is None:
            #pr(row, "rejecting because origin is null: ")
            imported = None
        else:
            imported = datetime.fromisoformat(origin)
    except TypeError:
        print("cannot parse {!r}".format(origin))
    SEEN += 1
    if row["SCHED_CODES"] is None:
        #pr(row, "Null scheduler codes: ")
        imported = None
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
    if SHITTY_TITLE.match(title):
        title = None
    
    path = RIVENDELL_SND + row["CUT_NAME"] + CUT_EXTENSION
    if not os.path.exists(path):
        print(f"skipping file not found: {path}")
        REJECTED += 1
        continue

    if not artist or not title:
        IDENTIFIED_VIA_ACOUSTID += 1
        if IDENTIFIED_VIA_ACOUSTID < 3:
            pr(row, f"let's ask AcousticId about {path}")
            for score, recording_id, title, artist in acoustid.match(ACOUSTID_KEY, path):
                print("Got {} / {} / {} / {}".format(score, recording_id, title, artist))

    if not artist or not title or not imported:
        REJECTED += 1
        continue


print(f"Seen {SEEN} entries from RDLibrary")
print(f"Skipped {REJECTED}")
print(f"Imported {IMPORTED}")
print(f"{IDENTIFIED_VIA_ACOUSTID} identified via Acoustid")

conn.close()
