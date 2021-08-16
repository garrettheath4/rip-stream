`rip-stream.py`
===============

Automatically downloads .ts files from a generated list of URLs and combines them together into an .mp4 file.
Simply run from a command line and follow the interactive prompts.

License: MIT

Usage
-----

`python3 rip-stream.py`

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

Attribution
-----------

Based on Bash script at https://stackoverflow.com/questions/22188332/download-ts-files-from-video-stream
