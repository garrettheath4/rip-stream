#!/usr/bin/env python3

"""
`rip-stream.py`
===============

Automatically downloads .ts files from a generated list of URLs and combines them together into an .mp4 file.
Simply run from a command line and follow the interactive prompts.

Usage
-----

``python3 rip-stream.py``

Installation
------------

.. code-block:: shell

   pip3 install pipenv  # If not already installed.
   pipenv install
   pipenv run python3 rip-stream.py
   # Then simply follow the interactive prompts.

Attribution
-----------

Inspired by Bash script at https://stackoverflow.com/a/45050718/1360295

"""

import sys
import os
import re
import logging
from functools import reduce
from pathlib import Path
import urllib.request
import glob

import ffmpeg
from tqdm import tqdm

__license__ = "MIT"

RAW_VIDEOS_DIR_NAME = "raw-ts-videos"

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


def main():
    if sys.version_info < (3, 6):
        raise RuntimeError("This script requires Python 3.6+")

    output_name = input('Episode name (like "S01E01 - Title"): ')
    raw_videos_dir = f"./{output_name}/{RAW_VIDEOS_DIR_NAME}"

    if os.path.isdir(raw_videos_dir):
        print(f"{raw_videos_dir} directory exists. Skipping download.")
    else:
        print('Please type a URL format and use "{}" as the placeholder for the video number.')
        print('If there are leading zeros in the video number use "{:03d}" as the placeholder instead (e.g. for "000").')
        print('Example: https://zype.com/videos{:03d}.ts')
        url_format = input('URL format: ')
        if '{' not in url_format or '}' not in url_format:
            raise ValueError("Placeholder not specified in URL format:", url_format)
        if re.search(r'{.*\..*}', url_format):
            raise ValueError("URL format placeholder cannot contain a `.` character:", url_format)
        first_index_str = input('First index (inclusive, default = 0): ')
        if first_index_str == "":
            first_index_int = 0
        else:
            first_index_int = int(first_index_str)
        # TODO: Automatically keep downloading the next incremented video until you get a 404 error
        last_index = int(input('Last index (inclusive, example: 555): '))

        index_range = range(first_index_int, last_index+1)

        download_all(url_format, index_range, raw_videos_dir)

    combined_ts_filename = f"./{output_name}/{output_name}.ts"
    if os.path.exists(combined_ts_filename):
        print(f"{combined_ts_filename} already exists. Skipping.")
    else:
        combine_all(raw_videos_dir, combined_ts_filename)

    output_mp4_filename = f"./{output_name}/{output_name}.mp4"
    if os.path.exists(output_mp4_filename):
        print(f"{output_mp4_filename} already exists. Skipping.")
    else:
        transcode_ts_to_mp4(combined_ts_filename, output_mp4_filename)
        # concat_and_transcode(raw_videos_dir, output_mp4_filename)
        # reduce_transcode(raw_videos_dir, output_mp4_filename)


def download_all(url_format: str, video_nums: range, raw_videos_dir: str):
    """
    Downloads all of the videos for a URL and Range into a folder with the given name.

    :param url_format: A string representing the format of the URL to download the raw videos from.
    :param video_nums: A `range` of valid video numbers to use in the urlFormat to generate download
                       URLs.
    :param raw_videos_dir: The name to give a new folder to download all new raw video files into.
    """

    if os.path.isdir(raw_videos_dir):
        raise RuntimeError("Raw video files download directory already exists.", raw_videos_dir)

    Path(raw_videos_dir).mkdir(parents=True)

    # NOTE: Optionally download playlist file if provided? (Maybe in a separate method)
    # download playlist file
    # playlistURL="$urlPrefix.m3u8"
    # $downloadCmd $downloadArg "$playlistURL" || exitOnError "Unable to download playlist file: $playlistURL"

    # NOTE: Optionally download key file if needed? (Maybe in a separate method)
    # download key file
    # keyURL="$(dirname "$urlPrefix")/ttBearer-1080.key"
    # $downloadCmd $downloadArg "$keyURL" || exitOnError "Unable to download key file: $keyURL"

    for i in tqdm(video_nums, desc='Downloading…', unit='vids'):
        urllib.request.urlretrieve(url_format.format(i), f"{raw_videos_dir}/{i:05}.ts")


def combine_all(raw_videos_dir: str, output_filename: str):
    """
    Combine all raw .ts videos from a given directory into a single file with the given filename.
    
    Example
    -------
    ``combine_all("./S01E01 - Pilot/raw-videos/")``
    
    Before
    ~~~~~~
      - ``./S01E01 - Pilot/raw-videos/000.ts``
      - ``./S01E01 - Pilot/raw-videos/001.ts``
      - ...
      - ``./S01E01 - Pilot/raw-videos/522.ts``
    
    After
    ~~~~~
      - **./S01E01 - Pilot/S01E01 - Pilot.ts**
      - ``./S01E01 - Pilot/raw-videos/000.ts``
      - ``./S01E01 - Pilot/raw-videos/001.ts``
      - ...
      - ``./S01E01 - Pilot/raw-videos/522.ts``
    
    :param raw_videos_dir: The name of the existing folder containing the raw files to combine
                           Example: ``"./S01E01 - Pilot/raw-videos/"``
    :param output_filename: Path of new .ts file to save.
                            Example: ``"./S01E01 - Pilot/S01E01 - Pilot.ts"``
    :raises RuntimeError: if raw-videos directory does not exist or output file exists
    """

    if not os.path.exists(raw_videos_dir):
        raise RuntimeError("raw-videos directory does not exist:", raw_videos_dir)

    if os.path.exists(output_filename):
        raise RuntimeError(f"Output file already exists.", output_filename)

    with open(output_filename, 'wb') as outfile:
        input_ts_filenames = sorted(glob.glob(f"{raw_videos_dir}/*.ts"))
        logger.debug(f"input_ts_filenames = {input_ts_filenames}")
        for ts_file in tqdm(input_ts_filenames, desc='Combining…', unit='vids'):
            with open(ts_file, 'rb') as infile:
                outfile.write(infile.read())
                # OR: cat "$inputFilename" >> "$outputFilename"


def transcode_ts_to_mp4(combined_ts_filename: str, output_mp4_filename: str):
    """
    Convert a given .ts video file to a valid .mp4 file using the **ffmpeg** library.

    :param combined_ts_filename: Input .ts file to convert
    :param output_mp4_filename: Output .mp4 file to create
    """

    print("Transcoding... (This could take a while...)")
    ffmpeg\
        .input(combined_ts_filename)\
        .output(output_mp4_filename)\
        .run()


if __name__ == "__main__":
    main()
