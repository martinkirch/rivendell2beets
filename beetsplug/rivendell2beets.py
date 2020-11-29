#!/usr/bin/env python3

from datetime import datetime
import re, os, sys, sqlite3, acoustid, time, logging

from beets import config
from beets.plugins import BeetsPlugin
from beets.ui import Subcommand
from beets.ui.commands import import_files

# I advise you to convert everything to FLAC first, with a bash loop and ffmpeg (and even ffmpeg-normalize)
# but if you wan to use Rivendell sounds directly, set this to ".wav"
CUT_EXTENSION = ".flac"

# tune this with your own scheduler code
SCHEDULER_CODE_MAP = {
'Creation': {}, # found: 2
'.': {}, # found: 13398
'Mu20142015': {}, # found: 904
'Mu20152016': {}, # found: 552
'MuAmbient': {'genre': 'Ambiant'}, # found: 222
'MuBassMsic': {'genre': 'Electro'}, # found: 21
'MuChanson': {'genre': 'Chanson'}, # found: 445
'MuClassic': {'genre': 'Classique'}, # found: 42
'MuCntryBlu': {'genre': 'Country-Blues'}, # found: 65
'MuCourt': {}, # found: 322
'MuDwnTempo': {'genre': 'Ambiant'}, # found: 87
'MuElectro': {'genre': 'Electro'}, # found: 3097
'MuExp': {'genre': 'Nuit'}, # found: 990
'MuExtreme': {'genre': 'Rock'}, # found: 7
'MuFolk': {'genre': 'Folk-Acoustique'}, # found: 818
'MuFR': {'language': 'fra'}, # found: 1241
'MuFunkSoul': {'genre': 'Funk-Soul'}, # found: 252
'MuGOLD': {}, # found: 681
'MuGroovRnB': {'genre': 'HipHop'}, # found: 10
'MuHipHop': {'genre': 'HipHop'}, # found: 720
'MuHouse': {'genre': 'Electro'}, # found: 56
'MuIndie': {'genre': 'Folk-Acoustique'}, # found: 308
'MuInstru': {}, # found: 80
'MuJazz': {'genre': 'Jazz'}, # found: 336
'MuLocal': {}, # found: 105
'MuLong': {}, # found: 47
'MuMathPost': {'genre': 'Rock'}, # found: 125
'MuMetal': {'genre': 'Rock'}, # found: 7
'MuMoins1An': {}, # found: 1022
'MuNoise': {'genre': 'Nuit'}, # found: 60
'MuPlayList': {}, # found: 750
'MuPop': {'genre': 'Pop'}, # found: 3042
'MuPunk': {'genre': 'Rock'}, # found: 16
'MuRap': {'genre': 'HipHop'}, # found: 22
'MuReggDub': {'genre': 'Reggae-Dub'}, # found: 247
'MuReprise': {}, # found: 4
'MuRock': {'genre': 'Rock'}, # found: 4572
'MuSTAR2014': {}, # found: 2
'MuTechno': {'genre': 'Electro'}, # found: 22
'MuWorldLat': {'genre': 'World-Latino'}, # found: 328
'Nuit': {'genre': 'Nuit'}, # found: 155
'Poesie': {}, # found: 5
'Poésie': {}, # found: 9
}


SHITTY_TITLE = re.compile(r"(\[new cart\])|(Untitled)|(Track\s+[0-9]+)", re.IGNORECASE)
TITLE_FIXER = re.compile(r"([A-Z]?[0-9]+\s*\-*\s*)?([^\-]{3,}) - (.*)")

def pr(entry, prefix=''):
    logging.info("%s%s: %s - %s [%s] %s",
        prefix,
        entry["CUT_NAME"],
        entry["ARTIST"],
        entry["TITLE"],
        entry["SCHED_CODES"],
        entry["ORIGIN_DATETIME"],
    )

class Rivendell2BeetsPlugin(BeetsPlugin):

    def __init__(self):
        super(Rivendell2BeetsPlugin, self).__init__()
        self.attributes = None

        self.IDENTIFIED_VIA_ACOUSTID = 0
        self.SEEN = 0
        self.IMPORTED = 0
        self.REJECTED = 0

        self._command_rivendell = Subcommand('rivendell2beets',
            help="Import from rivendell")
        self._command_rivendell.func = self._main

    def commands(self):
        return [self._command_rivendell]

    def on_import_begin(self, session):
        session.config['singletons'] = True
        config['import']['quiet'] = True

    def on_import_task_created(self, task, session):
        if self.attributes:
            logging.debug("Applying %s", self.attributes)
            task.item.update(self.attributes) # injects our own metadata
            return [task]
        return []

    def on_item_imported(self, lib, item):
        if self.attributes:
            item.update(self.attributes) # just to be sure (especially because we force "added")
            item.store()

    def _main(self, lib, opts, args):
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(filename)s:%(lineno)s] %(levelname)s %(message)s"
        )
        self.register_listener('import_begin', self.on_import_begin)
        self.register_listener('import_task_created', self.on_import_task_created)
        self.register_listener('item_imported', self.on_item_imported)

        if len(args) != 2:
            logging.error("Usage:\n\nbeet rivendell2beets [ACOUSTICID_KEY] [rivendellSoundFolder]")
            return None
        # path to Rivendell sounds (defaults to /srv/rivendell/snd/)
        RIVENDELL_SND = args[1]
        if RIVENDELL_SND[-1] != '/':
            RIVENDELL_SND = RIVENDELL_SND + '/'

        ACOUSTID_KEY = args[0]

        IMPORTATION_FAILURES = RIVENDELL_SND + "failed/"
        os.makedirs(IMPORTATION_FAILURES, exist_ok=True)

        conn = sqlite3.connect('rivendell.db')
        conn.row_factory = sqlite3.Row

        for row in conn.execute("""
        SELECT 
        ARTIST, TITLE, SCHED_CODES,
        CUT_NAME, ORIGIN_DATETIME
        FROM CART c
        JOIN CUTS cut ON CART_NUMBER = NUMBER
        WHERE GROUP_NAME='MUSIC'
        """):
            imported = None
            self.attributes = {}
            try:
                origin = row['ORIGIN_DATETIME']
                if origin is None:
                    pr(row, "rejecting because origin is null: ")
                    imported = None
                else:
                    imported = datetime.fromisoformat(origin)
            except TypeError:
                logging.error("cannot parse {!r}".format(origin))
            self.SEEN += 1
            if row["SCHED_CODES"] is None:
                pr(row, "Null scheduler codes: ")
                imported = None
            else:
                for code in row["SCHED_CODES"].split(" "):
                    if code:
                        self.attributes.update(SCHEDULER_CODE_MAP[code])
            artist = row["ARTIST"]
            title = row["TITLE"]
            if not artist:
                m = TITLE_FIXER.match(title)
                if m:
                    artist = m.group(2).strip()
                    title = m.group(3).strip()
            if SHITTY_TITLE.match(title):
                title = None

            path = RIVENDELL_SND + row["CUT_NAME"] + CUT_EXTENSION
            if not os.path.exists(path):
                logging.error(f"skipping file not found: {path}")
                self.REJECTED += 1
                path = None

            if path and (not artist or not title):
                pr(row, f"let's ask AcousticId about {path}")
                try:
                    for score, record_id, record_title, record_artist in acoustid.match(ACOUSTID_KEY, path):
                        logging.info("Got {} / {} / {} / {}".format(score, record_id, record_title, record_artist))
                        self.attributes['mb_trackid'] = record_id
                        artist = record_artist
                        title = record_title
                        self.IDENTIFIED_VIA_ACOUSTID += 1
                        break
                except acoustid.WebServiceError as error:
                    logging.error(error)
                # limit request rate to AcoustID (3 requests per seconds)
                time.sleep(0.3)

            if path and artist and title and imported:
                self.attributes["artist"] = artist
                self.attributes["title"] = title
                self.attributes["added"] = imported.isoformat()[0:19].replace('T', ' ')
                logging.info("Processing %s", path)
                import_files(lib, [path], None)
                self.IMPORTED += 1
            elif path:
                self.REJECTED += 1
                os.rename(path, "{}/{} - {} - {} - {}.{}".format(
                    IMPORTATION_FAILURES,
                    row["CUT_NAME"],
                    row["ARTIST"],
                    row["TITLE"],
                    row["SCHED_CODES"],
                    CUT_EXTENSION)
                )

        print(f"Seen {self.SEEN} entries from RDLibrary")
        print(f"Skipped {self.REJECTED}")
        print(f"Imported {self.IMPORTED}")
        print(f"{self.IDENTIFIED_VIA_ACOUSTID} identified via Acoustid")

        conn.close()
