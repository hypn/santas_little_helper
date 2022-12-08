#!/usr/bin/env python3

import websocket
import ssl
import json
import time
import getopt
import sys
import os
from datetime import date

login_user = 'youremailhere'
login_pass = None
which_year = "" # will default to the latest year if not set

off='\033[0m'
red='\033[0;91m'
grn='\033[0;32m'
yel='\033[0;33m'
blu='\033[0;34m'
prp='\033[0;35m'
cya='\033[0;36m'

if which_year == "":
    # determine which year to use (only use current year in December, otherwise previous year)
    year = int(date.today().strftime("%Y"))
    month = int(date.today().strftime("%m"))
    if month < 12:
        year = year - 1
    year = str(year)
else:
    year = which_year

# make the data directory (for the year) if it doesn't exist
if not os.path.exists("data/" + year):
    os.makedirs("data/" + year)

ws_url = 'wss://' + year + '.kringlecon.com/ws'

portal_data_file = 'data/' + year + '/portal_data.json'
extra_info_file = 'data/' + year + '/extra_info.json'
npc_chatter_file = 'data/' + year + '/npc_chatter.json'

enable_burp_proxy = False
proxy_h = "127.0.0.1"
proxy_p = 8080

######################################################################################################

ws = websocket.WebSocket(sslopt={"cert_reqs": ssl.CERT_NONE})

current_state = {}
known_portals = {}
extra_info = {}
npc_chatter = {}

def handle_response(r):
    global current_state
    global known_portals
    r_json = json.loads(r)
    m_type = r_json['type']

    debug(f"Received message of type {m_type}.")
    if m_type == "SET_LOCATIONS":
        current_state['locations'] = r_json['loc']
    elif m_type == "SET_ENTITYAREAS":
        current_state['entity_areas'] = r_json['entities']
    elif m_type == "WS_OHHIMARK":
        if r_json.get('userId'):
            current_state['own_user_id'] = r_json['userId']
    elif m_type == "AAANNNDD_SCENE":
        if current_state.get('current_area') != r_json['areaData']['shortName']:
            info(f"Server new current location: {r_json['areaData']['shortName']}")

        current_state['current_area'] = r_json['areaData']['shortName']

        # TODO: implement handling of things like elevators, for rooms without exits
        if 'exit' in r_json['areaData']['entities']:
            exits = r_json['areaData']['entities']['exit']
        else:
            exits = []

        # Add all exits for the current zone
        this_zone = known_portals.get(current_state['current_area'])
        if extra_info.get(current_state['current_area']) is None:
            extra_info[current_state['current_area']] = {}
        if this_zone is None:
            known_portals[current_state['current_area']] = {}
            this_zone = known_portals[current_state['current_area']]
            extra_info[current_state['current_area']]['display_name'] = r_json['areaData']['displayName']
            extra_info[current_state['current_area']]['grid'] = r_json['areaData']['grid']
        else:
            this_zone = known_portals[current_state['current_area']]
        for exit in exits:
            new_exit = this_zone.get(exit['id'])
            if new_exit is None:
                this_zone[exit['id']] = {}
                this_zone[exit['id']]['name'] = exit['id']
                this_zone[exit['id']]['x'] = exit['x']
                this_zone[exit['id']]['y'] = exit['y']
                discover(f"Found new portal from {current_state['current_area']} to {this_zone[exit['id']]['name']}")
    elif m_type == "SET_ENTITIES":
        for entity in r_json['entities']:
            if 'area' in r_json['entities'][entity]:
                room = r_json['entities'][entity]['area']
                if extra_info.get(room) is None:
                    extra_info[room] = {}
                if extra_info[room].get('entities') is None:
                    extra_info[room]['entities'] = {}
                if extra_info[room]['entities'].get(entity) is None:
                    extra_info[room]['entities'][entity] = {}
                    extra_info[room]['entities'][entity]['name'] = r_json['entities'][entity]['shortName']
                    extra_info[room]['entities'][entity]['display_name'] = r_json['entities'][entity]['displayName']
                    extra_info[room]['entities'][entity]['type'] = r_json['entities'][entity]['type']
                    extra_info[room]['entities'][entity]['location'] = r_json['entities'][entity]['location']
                    if extra_info[room]['entities'][entity]['type'] == 'npc':
                        discover(f"Found new NPC named '{extra_info[room]['entities'][entity]['display_name']}'")
                    elif extra_info[room]['entities'][entity]['type'] == 'terminal':
                        discover(f"Found new Terminal named '{extra_info[room]['entities'][entity]['display_name']}'")
                    elif extra_info[room]['entities'][entity]['type'] == 'item':
                        discover(f"Found new Item named '{extra_info[room]['entities'][entity]['display_name']}'")
                    else:
                        err(f"Found new unknown object named '{extra_info[room]['entities'][entity]['display_name']}'")
    elif m_type == "PSSST":
        for w in r_json['whisper']:
            uid = r_json['whisper'][w]['uid']
            message = r_json['whisper'][w]['text']
            if message not in npc_chatter[uid]:
                discover("Received new chat message")
                npc_chatter[uid].append(message)
    elif m_type == "OPEN_TERMINAL":
        term_id = r_json['id']
        url = r_json['url']
        for room in extra_info:
            if extra_info[room].get('entities') is None:
                continue
            for entity in extra_info[room]['entities']:
                if extra_info[room]['entities'][entity]['type'] == 'terminal' and extra_info[room]['entities'][entity]['name'] == term_id:
                    if 'url' not in extra_info[room]['entities'][entity]:
                        discover("Received new terminal url for \"" + term_id +"\"")
                    resource_id = r_json['resourceId']
                    extra_info[room]['entities'][entity]['url'] = url + "?challenge=" + term_id + '&id=123'
                    extra_info[room]['entities'][entity]['resource_url'] = url + "?challenge=" + term_id + '&id=123'
                    # extra_info[room]['entities'][entity]['resource_url'] = url + "?challenge=" + term_id + '&id=' + resource_id

    return m_type


def login():
    global login_pass
    info(f"Starting login for user {login_user}")

    if login_pass is None:
        login_pass = input("Please enter your password: ")
    else:
        err("WARNING: Plaintext credentials in script")

    ws.send('{"type":"WS_CONNECTED","protocol":"43ae08fd-9cf2-4f54-a6a6-8454aef59581"}')
    handle_response(ws.recv())
    ws.send('{"type":"WS_LOGIN","usernameOrEmail":"%s","password":"%s"}' % (login_user, login_pass))
    receive_until_new_area()
    receive_until_uid()


def receive_until_new_area():
    start_area = current_state.get('current_area')
    while current_state.get('current_area') == start_area:
        handle_response(ws.recv())


def receive_until_uid():
    while current_state.get('own_user_id') is None:
        handle_response(ws.recv())


def receive_until_siddown():
    while handle_response(ws.recv()) != 'SIDDOWN':
        pass


def receive_until_pssst():
    while handle_response(ws.recv()) != 'PSSST':
        pass


def receive_until_terminal():
    while handle_response(ws.recv()) not in ['OPEN_TERMINAL', 'DENNIS_NEDRY']:
        pass

def teleport_user(target_zone):
    ws.send('{"type":"TELEPORT_USER","destination":"%s"}' % (target_zone))
    receive_until_new_area()


def goto_zone(target_zone):
    current_zone = current_state['current_area']

    if target_zone == current_zone:
        return

    action(f"Full multi-zone move from {current_zone} to {target_zone}")
    path = list()
    real_ids = list()
    path.append(current_zone)
    real_ids.append(current_zone)
    path = goto_zone_recurse(current_zone, target_zone, path, real_ids)

    if path is None:
        err(f"Failed to find path to {target_zone} starting from {current_zone}")
        err(f"Please try moving somewhere else in-game")
        return
    for zone in path[1:]:
        goto_adjacent_zone(zone)

def goto_zone_recurse(start_zone, target_zone, path, real_ids):
    # Test neighbouring zones
    for option in known_portals[start_zone]:
        if known_portals[start_zone][option].get('real_id') == target_zone:
            path.append(known_portals[start_zone][option].get('name'))
            real_ids.append(known_portals[start_zone][option].get('real_id'))
            return path

    # Recurse
    for option in known_portals[start_zone]:
        next_zone = known_portals[start_zone][option].get('real_id')
        if next_zone:
            if next_zone in real_ids:
                continue
            else:
                tmp_path = list(path)
                tmp_real = list(real_ids)
                tmp_path.append(known_portals[start_zone][option].get('name'))
                tmp_real.append(known_portals[start_zone][option].get('real_id'))
                tmp_path = goto_zone_recurse(next_zone, target_zone, tmp_path, tmp_real)
                if tmp_path is not None:
                    return tmp_path

    return None


def goto_adjacent_zone(zone_id):
    current_zone = current_state['current_area']
    action(f"Moving from room {current_zone} to {zone_id}")

    if known_portals.get(current_zone) is None:
        err(f"Current zone ({current_zone}) exit portals not known")
        exit()
    if known_portals[current_zone].get(zone_id) is None:
        err(f"No path possible from {current_zone} to {zone_id}")
        print(known_portals)
        exit()

    uid = current_state['own_user_id']
    portal_x = known_portals[current_zone][zone_id]['x']
    portal_y = known_portals[current_zone][zone_id]['y']
    ws.send('{"type":"MOVE_USER","loc":{"%s":[%d,%d]},"areaId":"%s"}' % (uid, portal_x, portal_y, current_zone))
    time.sleep(1)
    ws.send('{"type":"REX","cell":[%d,%d]}' % (portal_x, portal_y))
    receive_until_new_area()

    # Add true link
    if known_portals[current_zone][zone_id].get('real_id') is None:
        known_portals[current_zone][zone_id]['real_id'] = current_state['current_area']
        good(f"Confirmed true portal from {current_zone} to {current_state['current_area']}")


def load_data():
    global known_portals
    global extra_info
    try:
        with open(portal_data_file) as json_file:
            good(f"Loading portal data from {portal_data_file}")
            known_portals = json.load(json_file)
    except:
        err(f"WARNING: No portal data found in file {portal_data_file}. Starting from nothing")
    try:
        with open(extra_info_file) as json_file:
            good(f"Loading extra info from {extra_info_file}")
            extra_info = json.load(json_file)
    except:
        err(f"WARNING: No extra info found in file {extra_info_file}. Starting from nothing")


def generate_data():
    good("Starting process of generating map data")

    another_round = True
    while another_round:
        another_round = False
        # Always try current zone neighbours first
        for portal in known_portals[current_state['current_area']]:
            if known_portals[current_state['current_area']][portal].get('real_id') is None:
                goto_adjacent_zone(portal)
                another_round = True
                break
        if another_round:
            continue

        # Only then check other zones for undiscovered areas
        for zone in known_portals:
            for portal in known_portals[zone]:
                if known_portals[zone][portal].get('real_id') is None:
                    goto_zone(zone)
                    goto_adjacent_zone(portal)
                    another_round = True
                    break
            if another_round:
                break

    # We also want to talk to all of the docker entities and grab their urls
    good("Grabbing docker links from all known terminal entities")
    for room in extra_info:
       if extra_info[room].get('entities') is None:
           continue
       for entity in extra_info[room]['entities']:
           if extra_info[room]['entities'][entity]['type'] == 'terminal':
               name = extra_info[room]['entities'][entity]['name']
               ws.send('{"type":"HELLO_ENTITY","entityType":"terminal","id":"%s"}' % name)
               receive_until_terminal()


    with open(portal_data_file, 'w') as outfile:
        good(f"Dumping portal data to {portal_data_file}")
        json.dump(known_portals, outfile, indent=2)
    with open(extra_info_file, 'w') as outfile:
        good(f"Dumping extra_info to {extra_info_file}")
        json.dump(extra_info, outfile, indent=2)


def teleport():
    print("")
    good("Starting teleportation module. Where would you like to go?")
    discover(f"Your current zone is {current_state['current_area']}")
    for zone in known_portals:
        print(f"- {zone} ({extra_info[zone]['display_name']})")

    print("")
    target = input("Please enter the zone shortname you would like to teleport to: ")

    if known_portals.get(target) is None:
        print(f"{red}That zone does not exist or is not known")

    starting_loc = current_state['current_area']
    if current_state['current_area'] == target:
        print("You're already at " + target)
    else:
        print("Trying to teleport to " + target)
        teleport_user(target)

        # check if we've been sent to "shenanigans" and if so return to starting location
        if current_state['current_area'] == "shenanigans" and target != "shenanigans":
            print(f"{yel}You've been moved to the \"shenanigans\" room! Moving back to {starting_loc}{off}")
            teleport_user(starting_loc)

        if current_state['current_area'] != target:
            if known_portals.get(target) is None:
                # walk to the target location if teleportation failed
                print(f"\n{yel}Trying to walk from {starting_loc} to {target} instead...{off}")
                goto_zone(target)
    print("")


def get_entities_for_zone(zone):
    terminals = list()
    npcs = list()
    if extra_info[zone].get('entities') is not None:
        for entity in extra_info[zone]['entities']:
            if extra_info[zone]['entities'][entity]['type'] == 'terminal':
                terminals.append(extra_info[zone]['entities'][entity])
            elif extra_info[zone]['entities'][entity]['type'] == 'npc':
                npcs.append(extra_info[zone]['entities'][entity])

    return (terminals, npcs)


def print_grid_specific(zone):
    discover(f"Name: {extra_info[zone]['display_name']}")
    print(f"{extra_info[zone]['grid']}")
    print("")

    (terminals, npcs) = get_entities_for_zone(zone)
    print(f"NPCs: ")
    for npc in npcs:
        print(f"- {npc['display_name']}")
    print("")
    print(f"Terminals: ")
    for term in terminals:
        term_name = term['name']
        ws.send('{"type":"HELLO_ENTITY","entityType":"terminal","id":"%s"}' % term_name)
        receive_until_terminal()
        r_url = extra_info[zone]['entities'][term_name]['resource_url']
        print(f"- {term['display_name']}  (url:{term['url']})")
        print(f"- Your personal link: {r_url}")
    print("")



def print_grid():
    print("")
    good("Starting cartographer module. Which map would you like to see?")
    print("- all")
    for zone in extra_info:
        print(f"- {zone} ({extra_info[zone]['display_name']})")

    print("")
    target = input("Please enter the zone shortname you would like to display the map for: ")

    if target == "all":
        for zone in extra_info:
            print_grid_specific(zone)
    elif extra_info.get(target) is None:
        err("That zone does not exist")
        exit()
    else:
        print_grid_specific(target)

    discover("In order to use the docker links here, you need to paste the following javascript in your developer console after loading the docker (if you do not, completing them will not score you any points in-game):")
    js_code = '''window.top.postMessage = function(message, other) {msg = '{"type":"COMPLETE_CHALLENGE","resourceId":"' + message.resourceId + '","hash":"' + message.hash + '"}';console.log(msg); ws = new WebSocket('wss://2020.kringlecon.com/ws'); ws.onopen = function () {      ws.send('{"type":"WS_CONNECTED","protocol":"43ae08fd-9cf2-4f54-a6a6-8454aef59581"}'); var passwd = prompt("Please enter your password", ""); ws.send('{"type":"WS_LOGIN","usernameOrEmail":"%s","password":"' + passwd + '"}'); setTimeout(function(){ ws.send(msg); }, 3000);     }}; '''
    js_code = js_code % login_user
    js_code = js_code.replace("wss://2020.kringlecon.com/ws", "wss://" + year + ".kringlecon.com/ws")
    print(js_code)

    print("")


def npc_talk(npc):
    action(f"Starting chat with NPC {npc}")
    if npc not in npc_chatter:
        npc_chatter[npc] = list()

    num_chats = len(npc_chatter[npc])
    num_chats_before = -1

    while num_chats < 50 and num_chats != num_chats_before:
        num_chats_before = num_chats
        ws.send('{"type":"HELLO_ENTITY","entityType":"npc","id":"%s"}' % npc)
        receive_until_pssst()
        num_chats = len(npc_chatter[npc])


def npc_talk_select():
    global npc_chatter
    try:
        with open(npc_chatter_file) as json_file:
            good(f"Loading chatter dump from {npc_chatter_file}")
            npc_chatter = json.load(json_file)
            npc_chatter_size = len(json.dumps(npc_chatter))
    except:
        err(f"WARNING: No npc chatter data found in file {npc_chatter_file}. Starting from nothing")
        npc_chatter = {}
        npc_chatter_size = 0

    print("")
    good("Starting chatter module. Which npc would you like to talk to?")
    print(f"- dump (Dumps all NPC chats to {npc_chatter_file})")
    npc_list = {}
    for room in extra_info:
        if extra_info[room].get('entities') is None:
            continue
        for entity in extra_info[room]['entities']:
            name = extra_info[room]['entities'][entity]['name']
            full_name = extra_info[room]['entities'][entity]['display_name']
            n_type = extra_info[room]['entities'][entity]['type']
            if n_type == 'npc':
                npc_list[name] = full_name

    for npc in npc_list:
        print(f"- {npc} ({npc_list[npc]})")

    print("")
    target = input("Please enter the npc shortname you would like to talk to: ")

    if target == "dump":
        for npc in npc_list:
            npc_talk(npc)
        with open(npc_chatter_file, 'w') as outfile:
            good(f"Dumping npc chatter data to {npc_chatter_file}")
            json.dump(npc_chatter, outfile, indent=2)
    elif npc_list.get(target) is None:
        err("That npc does not exist")
        exit()
    else:
        npc_talk(target)
        info(f"NPC: {npc_list[target]}")
        for message in npc_chatter[target]:
            print(f'- "{message}"')

    if npc_chatter_size != len(json.dumps(npc_chatter)):
        with open(npc_chatter_file, 'w') as outfile:
            good(f"Dumping npc chatter data to {npc_chatter_file}")
            json.dump(npc_chatter, outfile, indent=2)

    print("")


def list_items():
    if len(extra_info) > 0:
        good("Item locations (if any):")
        for zone in extra_info:
            if "entities" in extra_info[zone]:
                for entity in extra_info[zone]["entities"]:
                    if extra_info[zone]["entities"][entity]['type'] == "item" or extra_info[zone]["entities"][entity]['display_name'] == "Treasure Chest":
                        name = extra_info[zone]["entities"][entity]['display_name']
                        room = extra_info[zone]['display_name']
                        coords = extra_info[zone]["entities"][entity]['location']
                        print(f"- \"{yel}{name}{off}\" in \"{cya}{room}{off}\" at {cya}{coords}{off}")
    else:
        print(f"{red}No data! Use \"-c\" (\"--create_data\") to collect data.{off}")


def list_terminals():
    if len(extra_info) > 0:
        good("Terminal locations:")
        for zone in extra_info:
            if "entities" in extra_info[zone]:
                for entity in extra_info[zone]["entities"]:
                    if extra_info[zone]["entities"][entity]['type'] == "terminal":
                        name = extra_info[zone]["entities"][entity]['display_name']
                        room = extra_info[zone]['display_name']
                        coords = extra_info[zone]["entities"][entity]['location']
                        url = extra_info[zone]["entities"][entity]['url'] + '&id=1'
                        print(f"- \"{yel}{name}{off}\" in {cya}{room}{off} at {cya}{coords}{off} ({blu}{url}{off})")
        print(f"{red}Note: these links will not unlock progress or achievements in the game!{off}")
    else:
        print(f"{red}No data! Use \"-c\" (\"--create_data\") to collect data.{off}")


def main():
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hctgnix", ["help", "create_portal_file", "teleport", "print_grid", "npc-talk", "items", "terminals"])
    except getopt.GetoptError as error:
        err(str(error))
        usage()
        exit()

    banner()

    if len(opts) == 0:
        usage()
        exit()


    if enable_burp_proxy:
        info(f"Tunneling all requests through proxy {proxy_h}:{proxy_p}")
        ws.connect(ws_url, http_proxy_host=proxy_h, http_proxy_port=proxy_p)
    else:
        ws.connect(ws_url)


    for o, a in opts:
        if o in ("-h", "--help"):
            usage()
            exit()
        elif o in ("-c", "--create_data"):
            load_data()
            login()
            generate_data()
        elif o in ("-t", "--teleport"):
            load_data()
            login()
            teleport()
        elif o in ("-g", "--print_grid"):
            load_data()
            login()
            print_grid()
        elif o in ("-n", "--npc-talk"):
            load_data()
            login()
            npc_talk_select()
        elif o in ("-i", "--items"):
            load_data()
            list_items()
        elif o in ("-x", "--terminals"):
            load_data()
            list_terminals()

    good("DONE!")

def usage():
    print('Run this script with one of the following options:')
    info("-h | --help        -> Print this help")
    info("-c | --create_data -> Generate the data file needed for teleporting and other functions")
    info("-t | --teleport    -> Teleport to a new location")
    info("-g | --print_grid  -> Print grid data for a zone")
    info("-n | --npc-talk    -> Talk to a certain NPC")
    info("-i | --items       -> List items")
    info("-x | --terminals   -> List terminals")

def err(msg):
    print(f"{red}[-] {msg}{off}")

def good(msg):
    print(f"{grn}[+] {msg}{off}")

def action(msg):
    print(f"{cya}[!] {msg}{off}")

def discover(msg):
    print(f"{yel}[>] {msg}{off}")

def info(msg):
    print(f"[*] {msg}")

def debug(msg):
    #print(f"    {msg}")
    pass

def banner():
    print(f"")
    print(f"{yel}.▄▄ ·  ▄▄▄·  ▐ ▄ ▄▄▄▄▄ ▄▄▄· .▄▄ ·     ▄▄▌  ▪  ▄▄▄▄▄▄▄▄▄▄▄▄▌  ▄▄▄ .     ▄ .▄▄▄▄ .▄▄▌   ▄▄▄·▄▄▄ .▄▄▄  {red}"+"       {_}         ")
    print(f"{yel}▐█ ▀. ▐█ ▀█ •█▌▐█•██  ▐█ ▀█ ▐█ ▀.     ██•  ██ •██  •██  ██•  ▀▄.▀·    ██▪▐█▀▄.▀·██•  ▐█ ▄█▀▄.▀·▀▄ █·{red}"+"      *-=\         ")
    print(f"{yel}▄▀▀▀█▄▄█▀▀█ ▐█▐▐▌ ▐█.▪▄█▀▀█ ▄▀▀▀█▄    ██▪  ▐█· ▐█.▪ ▐█.▪██▪  ▐▀▀▪▄    ██▀▐█▐▀▀▪▄██▪   ██▀·▐▀▀▪▄▐▀▀▄ {red}"+"         \\____(   ")
    print(f"{yel}▐█▄▪▐█▐█ ▪▐▌██▐█▌ ▐█▌·▐█ ▪▐▌▐█▄▪▐█    ▐█▌▐▌▐█▌ ▐█▌· ▐█▌·▐█▌▐▌▐█▄▄▌    ██▌▐▀▐█▄▄▌▐█▌▐▌▐█▪·•▐█▄▄▌▐█•█▌{red}"+"        _|/---\\   ")
    print(f"{yel} ▀▀▀▀  ▀  ▀ ▀▀ █▪ ▀▀▀  ▀  ▀  ▀▀▀▀     .▀▀▀ ▀▀▀ ▀▀▀  ▀▀▀ .▀▀▀  ▀▀▀     ▀▀▀ · ▀▀▀ .▀▀▀ .▀    ▀▀▀ .▀  ▀{red}"+"        \        \ ")
    print(f" - A Kringlecon tool by Polle Vanhoof, updated for 2020+ by HypnInfoSec")
    print(f"{off}")


main()

