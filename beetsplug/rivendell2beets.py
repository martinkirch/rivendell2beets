#!/usr/bin/env python3
"""

TODO:
- howto force beet's import date ? -> test with drop2beets
- scheduler codes mapping

"""
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
 'MuCntryBlu': None,
 'Mu20142015': None,
 'MuExtreme': None,
 'MuLong': None,
 'MuFR': {'language': 'fra'},
 'MuElectro': None,
 'MuRock': None,
 'MuFolk': None,
 'Mu20152016': None,
 'MuMathPost': None,
 'MuBassMsic': None,
 'MuReprise': None,
 'MuHouse': None,
 'MuPop': None,
 'MuSTAR2014': None,
 'MuIndie': None,
 'MuWorldLat': None,
 'MuGOLD': None,
 'MuPlayList': None,
 'MuFunkSoul': None,
 'MuPunk': None,
 'MuChanson': None,
 'MuJazz': None,
 'Poesie': None,
 'MuAmbient': None,
 'MuHipHop': None,
 'MuNoise': None,
 'MuMetal': None,
 'MuClassic': None,
 'MuReggDub': None,
 'MuExp': None,
 'Poésie': None,
 'MuRap': None,
 'Nuit': None,
 'MuTechno': None,
 'MuCourt': None,
 'MuDwnTempo': None,
 '.': None,
 'MuLocal': None,
 'MuGroovRnB': None,
 'MuMoins1An': None,
 'MuInstru': None,
 'Creation': None,
}


SHITTY_TITLE = re.compile(r"(\[new cart\])|(Untitled)|(Track\s+[0-9]+)", re.IGNORECASE)
TITLE_FIXER = re.compile(r"([A-Z]?[0-9]+\s*\-*\s*)?([^\-]{3,}) - (.*)")

schedcodes = set()

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
        if self.attributes is None:
            logging.info("Importation aborted by on_item")
            return []
        else:
            logging.debug("Applying %s", self.attributes)
            return [task]

    def on_item_imported(self, lib, item):
        if self.attributes:
            item.update(self.attributes)
            item.store()

    def _main(self, lib, opts, args):
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s [%(filename)s:%(lineno)s] %(levelname)s %(message)s"
        )
        self.register_listener('import_begin', self.on_import_begin)
        self.register_listener('import_task_created', self.on_import_task_created)
        self.register_listener('item_imported', self.on_item_imported)

        if len(args != 2):
            logging.error("Usage:\n\nbeet rivendell2beets [ACOUSTICID_KEY] [rivendellSoundFolder]")
            return None
        # path to Rivendell sounds (defaults to /srv/rivendell/snd/)
        RIVENDELL_SND = args[1]
        if RIVENDELL_SND[-1] != '/':
            RIVENDELL_SND = RIVENDELL_SND + '/'

        ACOUSTID_KEY = args[0]

        IMPORTATION_FAILURES = RIVENDELL_SND + "failed/"
        os.mkdir(IMPORTATION_FAILURES)

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
            try:
                origin = row['ORIGIN_DATETIME']
                if origin is None:
                    #pr(row, "rejecting because origin is null: ")
                    imported = None
                else:
                    imported = datetime.fromisoformat(origin)
            except TypeError:
                print("cannot parse {!r}".format(origin))
            self.SEEN += 1
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
                    artist = m.group(2).strip()
                    title = m.group(3).strip()
            if SHITTY_TITLE.match(title):
                title = None

            path = RIVENDELL_SND + row["CUT_NAME"] + CUT_EXTENSION
            if not os.path.exists(path):
                print(f"skipping file not found: {path}")
                self.REJECTED += 1
                continue

            if not artist or not title:
                pr(row, f"let's ask AcousticId about {path}")
                found = None
                try:
                    for score, record_id, record_title, record_artist in acoustid.match(ACOUSTID_KEY, path):
                        print("Got {} / {} / {} / {}".format(score, record_id, record_title, record_artist))
                        found = record_title
                except acoustid.WebServiceError as error:
                    print(error)
                if found:
                    self.IDENTIFIED_VIA_ACOUSTID += 1
                # limit request rate to AcoustID (3 requests per seconds)
                time.sleep(0.3)

            if not artist or not title or not imported:
                self.REJECTED += 1
                continue
        
            self.attributes = {}
            # TODO use SCHEDULER_CODE_MAP


        print(f"Seen {self.SEEN} entries from RDLibrary")
        print(f"Skipped {self.REJECTED}")
        print(f"Imported {self.IMPORTED}")
        print(f"{self.IDENTIFIED_VIA_ACOUSTID} identified via Acoustid")

        conn.close()


        #_logger.info("Processing %s", filename)
        #full_path = "%s/%s" % (folder, filename)
        #import_files(lib, [full_path], None)

