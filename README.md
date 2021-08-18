`rip-stream.py`
===============

Automatically downloads .ts files from a generated list of URLs and combines them together into an .mp4 file.
Simply run from a command line and follow the interactive prompts.

License: MIT

Usage
-----

To run interactively (where _rip-stream_ asks you to type in everything it needs):

    pipenv run python3 rip-stream.py

or, if you already have the dependencies installed system-wide, simply run:

    python3 rip-stream.py

You can also run _rip-stream_ non-interactively by running it with command line arguments:

    python3 rip-stream.py --url_template 'https://example.com/videos/{}.ts' \
                          --first_number 0 'S01E01 - Pilot'

Run `python3 rip-stream.py --help` to learn more about the command line arguments.

Installation
------------

```shell
git clone https://github.com/garrettheath4/rip-stream.git
cd rip-stream        # Or cd to the directory where you want to store the temp downloaded and final .mp4 files.
pip3 install pipenv  # If not already installed.
pipenv install
pipenv run python3 rip-stream.py
```

Then simply follow the interactive prompts.

You can also optionally have _rip-stream_ send you a [Pushover](https://pushover.net) notification when it is done
transcoding. Simply create a `~/.pushoverrc` file (in your home directory) with the following contents:

```ini
[Default]
api_token=aaaaaa
user_key=xxxxxx
```

Dependencies
------------

* Python 3.7+
* [ffmpeg-python]
    * This Python library might require you to first install the main _ffmpeg_ library on your system.
      If you are using macOS, you can do this with [Homebrew](https://brew.sh) using `brew install ffmpeg`.
* [tqdm] – Makes it easy to display progress bars in the console from a Python script.
* [pyspin] - Displays loading spinner in the console.
* [python-pushover] – Optionally receive a Pushover notification every time _rip-stream_ finishes transcoding.

Attribution
-----------

Inspired by Bash script at https://stackoverflow.com/a/45050718/1360295



<!-- Links -->
[ffmpeg-python]: https://github.com/kkroening/ffmpeg-python
[tqdm]: https://tqdm.github.io
[pyspin]: https://github.com/lord63/py-spin
[python-pushover]: https://github.com/Thibauth/python-pushover
