# santas_little_helper
Kringlecon 2020 - An automated websocket tool

This is a tool [pollev](https://github.com/pollev) wrote for interacting with the backend server during the Kringlecon 2019 CTF. It allows you to pull relevant data from the backend through the websocket. It has been (partially) updated by [@HypnInfoSec](https://twitter.com/HypnInfoSec) from KringleCon 2020.

It generates map data and is able to start conversations with npc's anywhere on the map. But most importantly, it can teleport your character to (most) rooms in the Kringlecon CTF game. The elevator now poses a hurdle and this tool cannot navigate it properly. There is also no "automatic ending" to teleport to.

## Running in docker

```
docker run --rm -ti -v $PWD:/app python:3 bash
python3 -m pip install websocket_client
cd /app
python santas_little_helper.py
```

## Installation
Please install the following dependency first:

`python3 -m pip install websocket_client`

## Usage

To use this script, fill in your email address inside the script and then run it.

    -h | --help -> print this help
    -c | --create_data -> Generate the data file needed for teleporting and other functions
    -t | --teleport -> Teleport to a new location
    -g | --print_grid -> Print grid data for a zone
    -n | --npc-talk -> Talk to a certain NPC
