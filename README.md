# santas_little_helper
Kringlecon 2019+ automated websocket tool

This is a tool [pollev](https://github.com/pollev) wrote for interacting with the backend server during the Kringlecon 2019 CTF. It allows you to pull relevant data from the backend through the websocket. It has been (partially) updated by [@HypnInfoSec](https://twitter.com/HypnInfoSec) from KringleCon 2020 and beyond.

It generates map data and is able to start conversations with npc's anywhere on the map. But most importantly, it can teleport your character to (most) rooms in the Kringlecon. The elevator now poses a hurdle and this tool cannot navigate it properly.

## Running in docker

```
docker run --rm -ti -v $PWD:/app python:3 bash
python3 -m pip install websocket_client
cd /app
python santas_little_helper.py
```

## Running locally
Please install the following dependency first:

```
python3 -m pip install websocket_client
python3 santas_little_helper.py
```

## Usage

To use this script, fill in your email address near the top of the script (and set which KringleCon year you want to use it on - it will default to the latest Kringlecon). Run the python script (as above) and choose one of the command line options from the list below - you should use `-c` first to gather as much data as possible.

    -h | --help        -> Print this help
    -c | --create_data -> Generate the data file needed for teleporting and other functions
    -t | --teleport    -> Teleport to a new location
    -g | --print_grid  -> Print grid data for a zone
    -n | --npc-talk    -> Talk to a certain NPC
    -i | --items       -> List items
    -x | --terminals   -> List terminals

## Tips
* ensure you've created the data before trying to teleport/print/talk/etc
* if you want to collect the NPC chats before and after solving terminals, it's best to use an account that has NOT solved anything first (with the `-n` flag and then `dump` option), and then do the same with an account that has solved everything - this order is important as the script doesn't know which messags come first
* use the `-c` option after significant events (including any initial starting zone, or after using an elevator) as the script can't properly find or navigate to everything on its own
