#!/usr/bin/env python3

"""
`rip-stream.py`
===============

Automatically downloads .ts files from a URL template and combines them together into an .mp4 file.
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
from pathlib import Path
import urllib.request
import glob
import argparse

import ffmpeg
from tqdm import tqdm
from pushover import Client as Pushover

__license__ = "MIT"

RAW_VIDEOS_DIR_NAME = "raw-ts-videos"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("rip-stream.py")

if sys.version_info < (3, 6):
    logger.warning("This script requires Python 3.6+")


def main():
    parser = argparse.ArgumentParser(
        description='Automatically download .ts files from a URL template and combine them together into an .mp4 file.'
    )
    parser.add_argument('video_name', type=str,
                        help='Video name (like "S01E01 - Title")')
    parser.add_argument('--url_template', type=str, metavar='URL',
                        help='URL template, using {} or {:03d} for number placeholders')
    parser.add_argument('--first_number', type=int, metavar='INT',
                        help='First number in URL template to download. Must be a non-negative integer.')
    parser.add_argument('--last_number', type=int, metavar='INT',
                        help='Last number in URL template to download. Must be a non-negative integer.')
    parser.add_argument('--notify', dest='notify', action='store_true',
                        help='Send a Pushover push notification when transcoding finishes. (Default.)')
    parser.add_argument('--no-notify', dest='notify', action='store_false',
                        help='Disable sending a Pushover push notification when transcoding finishes.')
    parser.set_defaults(notify=True)
    parser.add_argument('--notification_level', type=int, default=0, metavar='LEVEL',
                        help='Priority of the notification to be sent. Valid values are -2, -1, 0, 1, 2. Default is 0.')

    args = parser.parse_args()
    logger.debug("args = %s", args.__dict__)
    if args.video_name and args.url_template and args.first_number >= 0 and args.last_number >= 0:
        download_and_transcode(args.video_name, url_template=args.url_template,
                               first_number=args.first_number, last_number=args.last_number,
                               notify=args.notify, notification_priority=args.notification_level)
    else:
        main_interactive()


def main_interactive():
    video_name = input('Video name (like "S01E01 - Title"): ')

    if not os.path.isdir(_raw_videos_dir(video_name)):
        print('Please type a URL template and use "{}" as the placeholder for the video number.')
        print('If there are leading zeros in the video number use "{:03d}" as the placeholder instead (e.g. for "000").')
        print('Example: https://zype.com/videos{:03d}.ts')
        url_template = input('URL template: ')
        if '{' not in url_template or '}' not in url_template:
            raise ValueError("Placeholder not specified in URL template:", url_template)
        if re.search(r'{.*\..*}', url_template):
            raise ValueError("URL template placeholder cannot contain a `.` character:", url_template)
        first_index_str = input('First index (inclusive, default = 0): ')
        if first_index_str == "":
            first_index_int = 0
        else:
            first_index_int = int(first_index_str)
        # TODO: Automatically keep downloading the next incremented video until you get a 404 error
        last_index = int(input('Last index (inclusive, example: 555): '))

        download_and_transcode(video_name, url_template, first_index_int, last_index)
    else:
        download_and_transcode(video_name)


def download_and_transcode(video_name: str,
                           url_template: str = None,
                           first_number: int = None, last_number: int = None,
                           notify: bool = True, notification_priority: int = 0):
    raw_videos_dir = _raw_videos_dir(video_name)

    if os.path.isdir(raw_videos_dir):
        logger.info("'%s' directory exists. Skipping download.", raw_videos_dir)
    else:
        index_range = range(first_number, last_number+1)
        download_all(url_template, index_range, raw_videos_dir)

    combined_ts_filename = f"./{video_name}/{video_name}.ts"
    if os.path.exists(combined_ts_filename):
        logger.info("'%s' already exists. Skipping.", combined_ts_filename)
    else:
        combine_all(raw_videos_dir, combined_ts_filename)

    output_mp4_filename = f"./{video_name}/{video_name}.mp4"
    if os.path.exists(output_mp4_filename):
        logger.info("'%s' already exists. Skipping.", output_mp4_filename)
    else:
        transcode_ts_to_mp4(combined_ts_filename, output_mp4_filename)

    if notify:
        if os.path.exists(os.path.expanduser('~/.pushoverrc')):
            notify_finished(video_name, notification_priority)
        else:
            logger.warning(
                "Create a ~/.pushoverrc file if you want to receive push notifications via Pushover.")


def notify_finished(video_name: str, priority: int = 0):
    Pushover().send_message(f"'{video_name}' finished transcoding.",
                            title="Rip-Stream Finished", priority=priority)


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
        raise RuntimeError("Output file already exists.", output_filename)

    with open(output_filename, 'wb') as outfile:
        input_ts_filenames = sorted(glob.glob(f"{raw_videos_dir}/*.ts"))
        logger.debug("input_ts_filenames = %s", input_ts_filenames)
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
    print(f"Transcode finished: {output_mp4_filename}")


def _raw_videos_dir(video_name: str) -> str:
    return f"./{video_name}/{RAW_VIDEOS_DIR_NAME}"


if __name__ == "__main__":
    main()
