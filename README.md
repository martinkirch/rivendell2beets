# Importing from RDLibrary to beets

This is a beet plug-in able to import music (it will only import from the MUSIC group)
from RDLibrary to [beets](https://beets.io).
It uses the "Artist" and "Title" tags from RDLibrary to re-tag files.
It also uses [acoustid](https://acoustid.org) to hopefully fix missing tags or wrong tags like `[new cart]`.

## Before starting

Identify where your Rivendell installation is storing its sounds (typically `/srv/rivendell/snd`).
Get a MySQL export of its database.

Install `pip3`, for example with `sudo apt-get install pip3`.

Install beets: As we're writing this the `beets` package downloaded by pip is still a bit out of date.
Therefore, if `pip3 install beets` installs version 1.4.9: rollback with `pip3 uninstall beets`
and clone from the main repository

    git clone https://github.com/beetbox/beets.git
    cd beets
    pip3 install -e .

In beets' configuration, you must enable this plug-in:
check that `rivendell2beets` is listed in `plugins`.

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
When you'll launch the import it must be in the current folder.

## Scheduler codes

The plugin contains a map of scheduler code : each code is associated either to `None`
or to a `dict` that will be merged with items' attributes.
See examples in source.

## The import itself

Launch it with

    beet rivendell2beets [ACOUSTICID_KEY] [rivendellSoundFolder]

Where

* `[rivendellSoundFolder]` is `/srv/rivendell/snd` or just `.` if you call this from a back-up.
* `[ACOUSTICID_KEY]` is your application's AcouticID API key

A file that is not correctly tagged in Rivendell (like "[new cart]", "Track 01" or nothing)
and not recoginzed by AcousticID will be moved to a "failed" subfolder,
renamed with the few things we knew form Rivendell. You will have to import those manually.
