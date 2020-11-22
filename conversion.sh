#!/bin/bash

# REQUIRES:
# sudo apt-get install ffmpeg
# pip3 install ffmpeg-normalize

set -e
cd /media/campus/f038cc5c-e1db-4a97-8c81-bb890109823d/srv/rivendell/snd
for f in *_001.wav
do
	echo "    $f"
	if ffmpeg-normalize -v $f -nt peak -t 0 -o /tmp/$f
	then
		if ffmpeg -i /tmp/$f ~/SndFromRivendell/${f/wav/flac}
		then
			rm /tmp/$f
			mv $f ../snd_converted/
		else
			echo "FAILED"
			exit 1
		fi
	else
		echo "FAILED"
		exit 1
	fi
done
