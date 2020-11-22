# Importing from RDLibrary to beets

This set of tools is able to import music (it will only import from the MUSIC group)
from RDLibrary to [beets](https://beets.io).
It uses the "Artist" and "Title" tags from RDLibrary to re-tag files.
It also uses [acoustid](https://acoustid.org) to hopefully fix missing tags or wrong tags like `[new cart]`.

## Before starting

Identify where your Rivendell installation is storing its sounds (typically `/srv/rivendell/snd`).
Get a MySQL export of its database.

Install `pip3`, for example with `sudo apt-get install pip3`.

Install beets: As we're writing this the `beets` package downloaded by pip is still a bit out of date.
Therefore, if you get version 1.4.9 with `pip3 install beets`:

* rollback with `pip3 uninstall beets`
* clone from the main repository:

    git clone https://github.com/beetbox/beets.git
    cd beets
    pip3 install -e .

Install [Chromaprint](https://acoustid.org/chromaprint):

    sudo apt-get install libchromaprint1
    pip3 install pyacoustid

You will need an AcouticID API key: register as an application at https://acoustid.org/

## Sound files

Rivendell converts everything to WAV files normalized at a LUFS scale ... which ended up quite low, in our experience. **Convert at least to FLAC** : it will use less disk space, and support metadata.
Our script also normalized to 0db peaks.

see `conversion.sh`. You'll have to:

* install ffmpeg and the `ffmpeg-normalize` package
* in `conversion.sh`
    - adjust the path to `srv/rivendell/snd` (Rivendell's WAV folder)
    - adjust the path to the target folder (currently `~/SndFromRivendell`)

## the DB

This repository includes `mysql2sqlite` as a submodule.
Convert your Rivendell DB dump to Sqlite with:

./mysql2sqlite database-20201118-0625.sql | sqlite3 rivendell.db

The result file, `rivendell.db`, will be used by the import script.
