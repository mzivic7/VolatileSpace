from configparser import ConfigParser
import os
import tkinter as tk
from tkinter import filedialog
import numpy as np

from volatilespace import defaults

settings = ConfigParser()
keybindings = ConfigParser()
settings.read("settings.ini")
home_dir = os.path.expanduser("~")


def export_file(file_name, filetype=[("All Files", "*.*")]):
    """save file with tkinter dialog"""
    root = tk.Tk()
    root.withdraw()
    if file_name == "":
        file_name = "New Map.ini"
    save_file = filedialog.asksaveasfile(mode='w', initialfile=file_name, defaultextension=".ini",
                                         initialdir=home_dir, filetypes=filetype)
    if save_file is None:   # asksaveasfile return "None" if dialog closed with "cancel"
        return ""
    file_path = save_file.name
    return file_path


def import_file(filetype=[("All Files", "*.*")]):
    """load file with tkinter dialog"""
    root = tk.Tk()
    root.withdraw()
    file_path = filedialog.askopenfilename(initialdir=home_dir, filetypes=filetype)   # open load file dialog and get path
    try:   # try to open file to see if it exists
        with open(file_path) as f:
            _ = f.read()
    except Exception:
        file_path = ""
    return file_path


def gen_game_list():
    """Generate list of maps in "Maps" dir. Name and edit date are read from file"""
    if not os.path.exists("Saves"):
        os.mkdir("Saves")
    files_list = os.listdir("Saves")
    
    # filter only files with .ini extension
    game_files = []
    for file_name in files_list:
        if file_name[-4:] == ".ini":
            game_files.append(file_name)
    
    # get data
    games = np.empty((0, 3), dtype=object)
    for game_file in game_files:
        game_save = ConfigParser()
        game_save.read("Saves/" + game_file)
        try:
            name = game_save.get("game_data", "name").strip('"')
            date = game_save.get("game_data", "date").strip('"')
            games = np.vstack((games, [game_file, name, date]))
        except Exception:
            pass

    # sort by name then by date
    games = games[games[:, 2].argsort()]
    games = games[games[:, 1].argsort(kind='mergesort')]
    
    # move quicksave and autosave at end
    for savetype in ["quicksave", "autosave"]:
        save_lst = np.where((games[:, 0] == savetype + ".ini"))[0]
        if len(save_lst) > 0:
            save_ind = save_lst[0]
            save_row = games[save_ind]
            games = np.delete(games, save_ind, 0)
            games = np.vstack((games, save_row))
    
    return games


def gen_map_list():
    """Generate list of maps in "Maps" dir. Name and edit date are read from file"""
    if not os.path.exists("Maps"):
        os.mkdir("Maps")
    files_list = os.listdir("Maps")
    
    # filter only files with .ini extension
    map_files = []
    for file_name in files_list:
        if file_name[-4:] == ".ini":
            map_files.append(file_name)
    
    # get data
    maps = np.empty((0, 3), dtype=object)
    for map_file in map_files:
        map_save = ConfigParser()
        map_save.read("Maps/" + map_file)
        try:
            name = map_save.get("game_data", "name").strip('"')
            date = map_save.get("game_data", "date").strip('"')
            maps = np.vstack((maps, [map_file, name, date]))
        except Exception:
            pass

    # sort by name then by date
    maps = maps[maps[:, 2].argsort()]
    maps = maps[maps[:, 1].argsort(kind='mergesort')]
    
    # move quicksave and autosave at end
    for savetype in ["quicksave", "autosave"]:
        save_lst = np.where((maps[:, 0] == savetype + ".ini"))[0]
        if len(save_lst) > 0:
            save_ind = save_lst[0]
            save_row = maps[save_ind]
            maps = np.delete(maps, save_ind, 0)
            maps = np.vstack((maps, save_row))
    return maps


def load_file(path):
    """Load saved data from map/saved game and returns type of save: newton/kepler"""
    system = ConfigParser()
    system.read(path)
    
    # read data section
    name = system.get("game_data", "name").strip('"')
    date = system.get("game_data", "date").strip('"')
    time = float(system.get("game_data", "time"))
    try:
        vessel = int(system.get("game_data", "vessel"))
    except Exception:
        vessel = None
    game_data = {"name": name, "date": date, "time": time, "vessel": vessel}
    
    # physics related config
    try:
        config = defaults.sim_config.copy()
        for key in defaults.sim_config.keys():
            value = float(system.get("config", key))
            config[key] = value
    except Exception:
        config = defaults.sim_config
    
    kepler = False
    body_name = np.array([])
    mass = np.array([])
    density = np.array([])
    color = np.empty((0, 3), int)
    atm_pres0 = np.array([])
    atm_scale_h = np.array([])
    atm_den0 = np.array([])
    
    vessel_name = np.array([])
    
    position = np.empty((0, 2), int)
    velocity = np.empty((0, 2), int)
    
    semi_major = np.array([])
    ecc = np.array([])
    pe_arg = np.array([])
    ma = np.array([])
    parents = np.array([], dtype=int)
    direction = np.array([])
    
    v_semi_major = np.array([])
    v_ecc = np.array([])
    v_pe_arg = np.array([])
    v_ma = np.array([])
    v_parents = np.array([], dtype=int)
    v_direction = np.array([])
    
    # load all body parameters into separate arrays
    for body in system.sections():
        if body not in ["game_data", "config"]:
            
            if not kepler:   # newtonian
                try:
                    position = np.vstack((position, list(map(float, system.get(body, "position").strip("][").split(", ")))))
                    velocity = np.vstack((velocity, list(map(float, system.get(body, "velocity").strip("][").split(", ")))))
                    body_name = np.append(body_name, body)
                    mass = np.append(mass, float(system.get(body, "mass")))
                    density = np.append(density, float(system.get(body, "density")))
                    color = np.vstack((color, list(map(int, system.get(body, "color").strip("][").split(", ")))))
                    try:
                        atm_pres0 = np.append(atm_pres0, float(system.get(body, "atm_pres0")))
                        atm_scale_h = np.append(atm_scale_h, float(system.get(body, "atm_scale_h")))
                        atm_den0 = np.append(atm_den0, float(system.get(body, "atm_den0")))
                    except Exception:
                        atm_pres0 = np.append(atm_pres0, 0.0)
                        atm_scale_h = np.append(atm_scale_h, 0.0)
                        atm_den0 = np.append(atm_den0, 0.0)
                except Exception:   # if pos or vel values are missing - then try to read kepler
                    kepler = True
            
            if kepler:
                if system.get(body, "obj") == "body":
                    body_name = np.append(body_name, body)
                    mass = np.append(mass, float(system.get(body, "mass")))
                    density = np.append(density, float(system.get(body, "density")))
                    color = np.vstack((color, list(map(int, system.get(body, "color").strip("][").split(", ")))))
                    try:
                        atm_pres0 = np.append(atm_pres0, float(system.get(body, "atm_pres0")))
                        atm_scale_h = np.append(atm_scale_h, float(system.get(body, "atm_scale_h")))
                        atm_den0 = np.append(atm_den0, float(system.get(body, "atm_den0")))
                    except Exception:
                        atm_pres0 = np.append(atm_pres0, 0.0)
                        atm_scale_h = np.append(atm_scale_h, 0.0)
                        atm_den0 = np.append(atm_den0, 0.0)
                    semi_major = np.append(semi_major, float(system.get(body, "sma")))
                    ecc = np.append(ecc, float(system.get(body, "ecc")))
                    pe_arg = np.append(pe_arg, float(system.get(body, "lpe")))
                    ma = np.append(ma, float(system.get(body, "mna")))
                    parents = np.append(parents, int(system.get(body, "ref")))
                    direction = np.append(direction, float(system.get(body, "dir")))
                elif system.get(body, "obj") == "vessel":
                    vessel_name = np.append(vessel_name, body)
                    v_semi_major = np.append(v_semi_major, float(system.get(body, "sma")))
                    v_ecc = np.append(v_ecc, float(system.get(body, "ecc")))
                    v_pe_arg = np.append(v_pe_arg, float(system.get(body, "lpe")))
                    v_ma = np.append(v_ma, float(system.get(body, "mna")))
                    v_parents = np.append(v_parents, int(system.get(body, "ref")))
                    v_direction = np.append(v_direction, float(system.get(body, "dir")))
    
    body_data = {"name": body_name, "mass": mass, "den": density, "color": color, "atm_pres0": atm_pres0, "atm_scale_h": atm_scale_h, "atm_den0": atm_den0}
    if kepler:
        body_orb_data = {"kepler": kepler, "a": semi_major, "ecc": ecc, "pe_arg": pe_arg, "ma": ma, "ref": parents, "dir": direction}
    else:
        body_orb_data = {"kepler": kepler, "pos": position, "vel": velocity}
    vessel_data = {"name": vessel_name}
    vessel_orb_data = {"a": v_semi_major, "ecc": v_ecc, "pe_arg": v_pe_arg, "ma": v_ma, "ref": v_parents, "dir": v_direction}
    
    return game_data, config, body_data, body_orb_data, vessel_data, vessel_orb_data


def save_file(path, game_data, conf, body_data, body_orb_data, vessel_data={}, vessel_orb_data={}):
    """Save system to file"""
    name = game_data["name"]
    date = game_data["date"]
    time = game_data["time"]
    vessel = game_data["vessel"]
    
    if not os.path.exists("Maps"):
        os.mkdir("Maps")
    if not os.path.exists("Saves"):
        os.mkdir("Saves")
    if name == "":
        name = "Unnamed"
    
    if os.path.exists(path):   # when overwriting
        if name is None:   # keep old name
            map_name = ConfigParser()
            map_name.read(path)
            try:
                name = map_name.get("game_data", "name").strip('"')
            except Exception:
                name = "New map"
        open(path, "w").close()   # delete file
    
    system = ConfigParser()
    system.read(path)
    
    system.add_section("game_data")
    system.set("game_data", "name", name)
    system.set("game_data", "date", date)
    system.set("game_data", "time", str(time))
    system.set("game_data", "vessel", str(vessel))
    
    system.add_section("config")   # special section for config
    for key in conf.keys():   # physics related config
        value = str(conf[key])
        system.set("config", key, value)
    
    body_names = body_data["name"]
    mass = body_data["mass"]
    density = body_data["den"]
    color = body_data["color"]
    atm_pres0 = body_data["atm_pres0"]
    atm_scale_h = body_data["atm_scale_h"]
    atm_den0 = body_data["atm_den0"]
    
    kepler = False
    try:
        position = body_orb_data["pos"]
        velocity = body_orb_data["vel"]
    except Exception:
        kepler = True
        semi_major = body_orb_data["a"]
        ecc = body_orb_data["ecc"]
        pe_arg = body_orb_data["pe_arg"]
        ma = body_orb_data["ma"]
        parents = body_orb_data["ref"]
        direction = body_orb_data["dir"]
    
    
    for body, body_name in enumerate(body_names):
        body_mass = mass[body]
        
        # handle if this body already exists
        num = 1
        while body_name in system.sections():
            body_name = body_names[body] + " " + str(num)
            num += 1
        
        system.add_section(body_name)
        
        if kepler:
            system.set(body_name, "obj", "body")
        
        system.set(body_name, "mass", str(body_mass))
        system.set(body_name, "density", str(density[body]))
        system.set(body_name, "color", "[" + str(color[body, 0]) + ", " + str(color[body, 1]) + ", " + str(color[body, 2]) + "]")
        if all(x != 0 for x in [atm_pres0[body], atm_scale_h[body], atm_den0[body]]):
            system.set(body_name, "atm_pres0", str(atm_pres0[body]))
            system.set(body_name, "atm_scale_h", str(atm_scale_h[body]))
            system.set(body_name, "atm_den0", str(atm_den0[body]))
        
        if not kepler:
            system.set(body_name, "position", "[" + str(position[body, 0]) + ", " + str(position[body, 1]) + "]")
            system.set(body_name, "velocity", "[" + str(velocity[body, 0]) + ", " + str(velocity[body, 1]) + "]")
            
        else:
            system.set(body_name, "sma", str(semi_major[body]))
            system.set(body_name, "ecc", str(ecc[body]))
            system.set(body_name, "lpe", str(pe_arg[body]))
            system.set(body_name, "mna", str(ma[body]))
            system.set(body_name, "ref", str(int(parents[body])))
            system.set(body_name, "dir", str(int(direction[body])))
    
    if vessel_data:
        vessel_names = vessel_data["name"]
        semi_major = vessel_orb_data["a"]
        ecc = vessel_orb_data["ecc"]
        pe_arg = vessel_orb_data["pe_arg"]
        ma = vessel_orb_data["ma"]
        parents = vessel_orb_data["ref"]
        direction = vessel_orb_data["dir"]
        
        for vessel, vessel_name in enumerate(vessel_names):
            
            # handle if this vessel already exists
            num = 1
            while vessel_name in system.sections():
                vessel_name = vessel_name[vessel] + " " + str(num)
                num += 1
        
            system.add_section(vessel_name)
            system.set(vessel_name, "obj", "vessel")
            system.set(vessel_name, "sma", str(semi_major[vessel]))
            system.set(vessel_name, "ecc", str(ecc[vessel]))
            system.set(vessel_name, "lpe", str(pe_arg[vessel]))
            system.set(vessel_name, "mna", str(ma[vessel]))
            system.set(vessel_name, "ref", str(int(parents[vessel])))
            system.set(vessel_name, "dir", str(int(direction[vessel])))
    
    with open(path, 'w') as f:
        system.write(f)


def new_map(name, date):
    """Creates new map with initial body and saves to file."""
    if not os.path.exists("Maps"):
        os.mkdir("Maps")
    if name == "":
        name = "New Map"
    
    # prevent having same name maps
    map_list = gen_map_list()
    new_name = name
    num = 1
    while new_name in map_list[:, 1] or new_name + ".ini" in map_list[:, 0]:
        new_name = name + " " + str(num)
        num += 1
    
    path = "Maps/" + new_name + ".ini"
    
    if os.path.exists(path):   # when overwriting, delete file
        open(path, "w").close()
    
    system = ConfigParser()   # load config class
    system.read(new_name + ".ini")   # load system
    
    system.add_section("game_data")
    system.set("game_data", "name", new_name)
    system.set("game_data", "date", date)
    system.set("game_data", "time", "0")
    
    system.add_section("config")   # special section for config
    for key in defaults.sim_config.keys():   # physics related config
        value = str(defaults.sim_config[key])
        system.set("config", key, value)
    
    system.add_section("root")
    system.set("root", "mass", "10000.0")
    system.set("root", "density", "1.0")
    system.set("root", "position", "[0.0, 0.0]")
    system.set("root", "velocity", "[0.0, 0.0]")
    system.set("root", "color", "[255, 255, 255]")
    
    with open(path, 'w') as f:
        system.write(f)
    
    return path


def rename_map(path, name):
    """Renames map without renaming file"""
    system = ConfigParser()
    system.read(path)
    if name == "":
        name = "Unnamed"
    
    # prevent having same name maps
    map_list = gen_map_list()
    new_name = name
    num = 1
    while new_name in map_list[:, 1]:
        new_name = name + " " + str(num)
        num += 1
    
    system.set("game_data", "name", new_name)
    with open(path, 'w') as f:
        system.write(f)


def new_game(name, date):
    """Creates new game with initial body and saves to file."""
    if not os.path.exists("Saves"):
        os.mkdir("Saves")
    if name == "":   # there must be name
        name = "New Map"
    
    # prevent having same name games
    game_list = gen_game_list()
    new_name = name
    num = 1
    while new_name in game_list[:, 1] or new_name + ".ini" in game_list[:, 0]:
        new_name = name + " " + str(num)
        num += 1
    
    path = "Saves/" + new_name + ".ini"
    if os.path.exists(path):   # when overwriting, delete file
        open(path, "w").close()
    
    system = ConfigParser()
    system.read(new_name + ".ini")
    
    system.add_section("game_data")
    system.set("game_data", "name", new_name)
    system.set("game_data", "date", date)
    system.set("game_data", "time", "0")
    
    system.add_section("config")   # special section for config
    
    with open(path, 'w') as f:
        system.write(f)
    
    return path


def rename_game(path, name):
    """Renames game without renaming file"""
    game = ConfigParser()
    game.read(path)
    if name == "":   # there must be name
        name = "Unnamed"
    
    # prevent having same name games
    game_list = gen_game_list()
    new_name = name
    num = 1
    while new_name in game_list[:, 1]:
        new_name = name + " " + str(num)
        num += 1
    
    game.set("game_data", "name", new_name)
    with open(path, 'w') as f:
        game.write(f)


def save_settings(header, key, value):
    """Saves value of specified setting to settings file"""
    try:
        settings.set(header, key, str(value))
    except Exception:
        settings.add_section(header)
        settings.set(header, key, str(value))
    with open("settings.ini", "w") as f:
        settings.write(f)


def load_settings(header, key):
    """load one or multiple settings from same header in settings file.
    Key must be str, tuple or list. If loading failed, create that header/setting."""
    try:
        if isinstance(key, str):   # if key is string (there is only one key)
            setting = settings.get(header, key)
            if "[" in setting and "]" in setting:   # if returned value is list
                setting = list(map(float, setting.strip("][").split(", ")))   # str to list of float
                if all(x.is_integer() for x in setting):   # if all values are whole number
                    setting = list(map(int, setting))   # float to int
        else:   # if it is not string, it should be tuple or list
            setting = []
            for one_key in key:   # for one key in keys
                one_setting = settings.get(header, one_key)
                if "[" in one_setting and "]" in one_setting:   # if returned value is list
                    one_setting = list(map(float, one_setting.strip("][").split(", ")))
                    if all(x.is_integer() for x in one_setting):
                        one_setting = list(map(int, one_setting))
                setting.append(one_setting)
    except Exception:
        setting = defaults.settings.get(key)   # load default setting and save it
        save_settings(header, key, setting)
    return setting


def delete_settings():
    """Removes all text from settings.ini so settings can be reverted to default"""
    open("settings.ini", "w").close()


def default_keybindings():
    """ Restores default keybindings to keybindings.ini"""
    keyb_dict = defaults.keybindings
    keybindings["keybindings"] = keyb_dict
    with open("keybindings.ini", "w") as f:
        keybindings.write(f)
    

def save_keybindings(keyb_dict):
    """Saves all keybindings to keybindings.ini"""
    keybindings["keybindings"] = keyb_dict
    with open("keybindings.ini", "w") as f:
        keybindings.write(f)


def load_keybindings():
    """Loads all keybindings from keybindings.ini"""
    try:
        keybindings.read("keybindings.ini")
        keyb_dict = dict(keybindings["keybindings"])
        # convert all dict values to int
        keyb_dict = dict([key, int(value)] for key, value in keyb_dict.items())
        if len(keyb_dict) != len(defaults.keybindings):
            keyb_dict = defaults.keybindings
            default_keybindings()
    except Exception:
        keyb_dict = defaults.keybindings
        default_keybindings()
    return keyb_dict
