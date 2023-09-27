import tkinter as tk
from tkinter import filedialog
import numpy as np
import os
from configparser import ConfigParser

from volatilespace import defaults

settings = ConfigParser()
keybindings = ConfigParser()
settings.read("settings.ini")
home_dir = os.path.expanduser("~")


def save_file(file_name, filetype=[("All Files", "*.*")]):
    """save file with tkinter dialog"""
    root = tk.Tk()   # define tkinter root
    root.withdraw()   # make tkinter root invisible
    if file_name == "":
        file_name = "new map.ini"
    save_file = filedialog.asksaveasfile(mode='w', initialfile=file_name, defaultextension=".ini",
                                         initialdir=home_dir, filetypes=filetype)
    if save_file is None:   # asksaveasfile return "None" if dialog closed with "cancel"
        return ""
    file_path = save_file.name   # get path
    return file_path


def load_file(filetype=[("All Files", "*.*")]):
    """load file with tkinter dialog"""
    root = tk.Tk()   # define tkinter root
    root.withdraw()   # make tkinter root invisible 
    file_path = filedialog.askopenfilename(initialdir=home_dir, filetypes=filetype)   # open load file dialog and get path
    try:   # just try to open file to see if it exists
        with open(file_path) as f:
            text = f.read()   # load all text from file
    except Exception:   # if cant open file
        file_path = ""
    return file_path


def gen_map_list():
    """Generate list of maps in "Maps" dir. Name and edit date are read from file"""
    if not os.path.exists("Maps"):   # if maps dir is deleted
        os.mkdir("Maps")
    files_list = os.listdir("Maps")   # generate list of files
    
    map_files = []
    for file_name in files_list:
        if file_name[-4:] == ".ini":   # filter only files with .ini extension
            map_files.append(file_name)
    
    maps = np.empty((len(map_files), 3), dtype=object)
    for num, map_file in enumerate(map_files):
        map_save = ConfigParser()
        map_save.read("Maps/" + map_file)
        try:
            name = map_save.get("config", "name").strip('"')
            date = map_save.get("config", "date").strip('"')
        except Exception:
            name = "Unknown"
            date = "-"
        maps[num, :] = np.array([map_file, name, date])
    
    maps = maps[maps[:, 2].argsort()]   # sort by name then by date
    maps = maps[maps[:, 1].argsort(kind='mergesort')]
    return maps


def load_system(path):
    """Load system from file"""
    system = ConfigParser()   # load config class
    system.read(path)   # load system
    
    name = system.get("config", "name").strip('"')
    time = float(system.get("config", 'time'))
    
    body_name = np.array([])
    mass = np.array([])  # mass
    density = np.array([])  # density
    position = np.empty((0, 2), int)   # position
    velocity = np.empty((0, 2), int)   # velocity
    color = np.empty((0, 3), int)   # color
    
    for body in system.sections():   # for each body:
        if body != "config":
            body_name = np.append(body_name, body)   # load all body parameters into separate arrays
            mass = np.append(mass, float(system.get(body, "mass")))
            density = np.append(density, float(system.get(body, "density")))
            position = np.vstack((position, list(map(float, system.get(body, "position").strip('][').split(', ')))))
            velocity = np.vstack((velocity, list(map(float, system.get(body, "velocity").strip('][').split(', ')))))
            color = np.vstack((color, list(map(int, system.get(body, "color").strip('][').split(', ')))))
    
    return name, time, body_name, mass, density, position, velocity, color


def save_system(path, name, date, time, body_names, mass, density, position, velocity, color):
    """Save system to file"""
    if not os.path.exists("Maps"):
        os.mkdir("Maps")
    if os.path.exists(path):   # when overwriting, delete file
        open(path, "w").close()
    system = ConfigParser()   # load config class
    system.read(path)   # load system
    
    system.add_section("config")   # special section for config
    system.set("config", "name", name)
    system.set("config", "date", date)
    system.set("config", "time", str(time))
    
    for body, body_mass in enumerate(mass):   # for each body:
        body_name = body_names[body]
        system.add_section(body_name)   # add body
        system.set(body_name, "mass", str(body_mass))   # add body parameters
        system.set(body_name, "density", str(density[body]))
        system.set(body_name, "position", '[' + str(position[body, 0]) + ', ' + str(position[body, 1]) + ']')
        system.set(body_name, "velocity", '[' + str(velocity[body, 0]) + ', ' + str(velocity[body, 1]) + ']')
        system.set(body_name, "color", '[' + str(color[body, 0]) + ', ' + str(color[body, 1]) + ', ' + str(color[body, 2]) + ']')
    
    with open(path, 'w') as f:
        system.write(f)


def new_map(name, date):
    """Creates new map with initial body and saves to file."""
    if not os.path.exists("Maps"):
        os.mkdir("Maps")
    path = "Maps/" + name + ".ini"
    if os.path.exists(path):   # when overwriting, delete file
        open(path, "w").close()
    system = ConfigParser()   # load config class
    system.read(name + ".ini")   # load system
    
    system.add_section("config")   # special section for config
    system.set("config", "name", name)
    system.set("config", "date", date)
    system.set("config", "time", "0")
    
    system.add_section("root")   # add body
    system.set("root", "mass", "10000.0")   # add body parameters
    system.set("root", "density", "1.0")
    system.set("root", "position", "[0.0, 0.0]")
    system.set("root", "velocity", "[0.0, 0.0]")
    system.set("root", "color", "[255, 255, 255]")
    
    with open(path, 'w') as f:
        system.write(f)
    
    return path


def rename_map(path, new_name):
    system = ConfigParser()
    system.read(path)
    system.set("config", "name", new_name)
    with open(path, 'w') as f:
        system.write(f)
    


def save_settings(header, key, value):
    """Saves value of specified setting to settings file"""
    try:
        settings.set(header, key, str(value))
    except Exception:   # if section is invalid
        settings.add_section(header)
        settings.set(header, key, str(value))
    with open("settings.ini", "w") as f:
        settings.write(f)


def load_settings(header, key):
    """load one or multiple settings from same header in settings file.
    Key must be str, tuple or list. If loading failed, create that header/setting."""
    try:
        if type(key) is str:   # if key is string (there is only one key)
            setting = settings.get(header, key)   # get value for that key
            if "[" in setting and "]" in setting:   # if returned value is list
                setting = list(map(float, setting.strip('][').split(', ')))   # str to list of float
                if all(x.is_integer() for x in setting):   # if all values are whole number
                    setting = list(map(int, setting))   # float to int
        else:   # if it is nost string, it should be tuple or list
            setting = []  # initial setting list
            for one_key in key:   # for one key in keys
                one_setting = settings.get(header, one_key)   # get value for that key
                if "[" in one_setting and "]" in one_setting:   # if returned value is list
                    one_setting = list(map(float, one_setting.strip('][').split(', ')))   # str to list of float
                    if all(x.is_integer() for x in one_setting):   # if all values are whole number
                        one_setting = list(map(int, one_setting))   # float to int
                setting.append(one_setting)   # append value to setting list
    except Exception:   # if setting is missing
        setting = defaults.settings.get(key)   # load default setting
        save_settings(header, key, setting)   # save default setting to settings.ini
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
