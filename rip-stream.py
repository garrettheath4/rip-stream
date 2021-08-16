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

Based on Bash script at https://stackoverflow.com/questions/22188332/download-ts-files-from-video-stream

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
        first_index = int(input('First index (inclusive): '))
        last_index = int(input('Last index (inclusive):  '))

        index_range = range(first_index, last_index+1)

        download_all(url_format, index_range, output_name)

    combined_ts_filename = f"./{output_name}/{output_name}.ts"
    if os.path.exists(combined_ts_filename):
        print(f"{combined_ts_filename} already exists. Skipping.")
    else:
        combine_all(raw_videos_dir, combined_ts_filename)

    # TODO: Transcode output file into a proper .mp4 using ffmpeg
    output_mp4_filename = f"./{output_name}/{output_name}.mp4"
    if os.path.exists(output_mp4_filename):
        print(f"{output_mp4_filename} already exists. Skipping.")
    else:
        # TODO: Ideally concat and transcode within ffmpeg
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


def flat_map(f, xs):
    ys = []
    for x in xs:
        ys.extend(f(x))
    return ys


def transcode_ts_to_mp4(combined_ts_filename: str, output_mp4_filename: str):
    """
    Convert a given .ts video file to a valid .mp4 file using the **ffmpeg** library.

    :param combined_ts_filename: Input .ts file to convert
    :param output_mp4_filename: Output .mp4 file to create
    """

    #TODO: Use ffmpeg to combine videos instead of manually combining them?
    ffmpeg\
        .input(combined_ts_filename)\
        .output(output_mp4_filename)\
        .run()


def concat_and_transcode(raw_videos_dir: str, output_mp4_filename: str):
    """
    Concatenate a list of .ts video files into one output .mp4 video file.

    :param raw_videos_dir: Directory containing the raw .ts input video files.
    :param output_mp4_filename: Filename to save the output .mp4 video file as.
    """

    # TODO: This whole method doesn't work. :-/
    # ffmpeg doesn't seem to be able to handle hundreds of streams (especially since these are probably done in-memory)
    raise NotImplementedError("concat_and_transcode")

    # in1 = ffmpeg.input('1.ts')
    # in2 = ffmpeg.input('2.ts')
    # v1 = in1.video
    # a1 = in1.audio
    # v2 = in2.video
    # a2 = in2.audio
    # l = [v1, a1, v2, a2]
    # ffmpeg.concat(*l, v=1, a=1).output('output.mp4').run()

    # ins = ['1.ts', '2.ts']
    # l = flat_map(lambda i: [i.video, i.audio], ins)
    # ffmpeg.concat(*l, v=1, a=1).output('output.mp4').run()

    input_ts_filenames = sorted(glob.glob(f"{raw_videos_dir}/*.ts"))
    input_videos = map(lambda s: ffmpeg.input(s), input_ts_filenames)
    split_stream_pairs = flat_map(lambda i: [i.video, i.audio], input_videos)
    ffmpeg.concat(*split_stream_pairs, v=1, a=1).output(output_mp4_filename).run()


def reduce_transcode(raw_videos_dir: str, output_mp4_filename: str):
    """
    Fully combine and transcode each video in the given dir (beginning with the 1st) into a new output .mp4 video file.

    :param raw_videos_dir: Directory containing the raw .ts input video files.
    :param output_mp4_filename: Filename to save the output .mp4 video file as.
    """
    input_ts_filenames = sorted(glob.glob(f"{raw_videos_dir}/*.ts*"))

    #TODO: This whole method doesn't work. :-/
    raise NotImplementedError("reduce_transcode")

    # OPTION 1
    # def add_filenames(filename_1: str, filename_2: str):
    #     input_1 = ffmpeg.input(filename_1)
    #     input_2 = ffmpeg.input(filename_2)
    #     ffmpeg \
    #         .concat(input_1.video, input_1.audio, input_2.video, input_2.audio, v=1, a=1) \
    #         .output(output_mp4_filename) \
    #         .run(overwrite_output=True)
    #     return output_mp4_filename
    # input_videos = map(lambda s: ffmpeg.input(s), input_ts_filenames)

    # OPTION 2
    # def add_input_videos(input_1: ffmpeg.nodes.FilterableStream, input_2: ffmpeg.nodes.FilterableStream):
    #     ffmpeg\
    #         .concat(input_1.video, input_1.audio, input_2.video, input_2.audio, v=1, a=1)\
    #         .output(output_mp4_filename)\
    #         .run(overwrite_output=True)
    #     return ffmpeg.input(output_mp4_filename)

    # reduce(add_input_videos, input_videos)

    # OPTION 3
    # stream = ffmpeg
    # for ts_file in tqdm(input_ts_filenames, desc='Combining…', unit='vids'):
    #     ts_input = ffmpeg.input(ts_file)
    #     stream = stream.concat(ts_input.video, ts_input.audio, v=1, a=1)
    # stream.output(output_mp4_filename).run()


if __name__ == "__main__":
    main()
