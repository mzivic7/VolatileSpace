import tkinter as tk
from tkinter import filedialog
import numpy as np
from configparser import ConfigParser

settings = ConfigParser()   # load config class
settings.read("settings.ini")   # load settings
    

def save_file(file_path):
    """save file with tkinter dialog"""
    root = tk.Tk()   # define tkinter root
    root.withdraw()   # make tkinter root invisible
    if file_path == "":
        file_path = "New_system.ini"
    save_file = filedialog.asksaveasfile(mode='w', initialfil=file_path, defaultextension=".txt", 
                                         filetypes=[("All Files", "*.*"), ("Text Documents", "*.txt")])
    if save_file is None:   # asksaveasfile return "None" if dialog closed with "cancel"
        return ""
    file_path = save_file.name   # get path
    return file_path


def load_file():
    """load file with tkinter dialog"""
    root = tk.Tk()   # define tkinter root
    root.withdraw()   # make tkinter root invisible
    file_path = filedialog.askopenfilename()   # open load file dialog and get path
    try:   # just try to open file to see if it exists
        with open(file_path) as file:
            text = file.read()   # load all text from file
    except Exception:   # if cant open file
        print("Error: File not found")
        file_path = ""
    return file_path


def load_system(path):
    """Load system from file"""
    system = ConfigParser()   # load config class
    system.read(path)   # load system
    
    mass = np.array([])  # mass
    density = np.array([])  # density
    position = np.empty((0, 2), int)   # position
    velocity = np.empty((0, 2), int)   # velocity
    color = np.empty((0, 3), int)   # color
    
    for body in system.sections():   # for each body:
        if body != "config":
            mass = np.append(mass, float(system.get(body, "mass")))   # load all body parameters into separate arrays
            density = np.append(density, float(system.get(body, "density")))
            position = np.vstack((position, list(map(float, system.get(body, "position").strip('][').split(', ')))))
            velocity = np.vstack((velocity, list(map(float, system.get(body, "velocity").strip('][').split(', ')))))
            color = np.vstack((color, list(map(int, system.get(body, "color").strip('][').split(', ')))))
        if body == "config":
            time = float(system.get(body, 'time'))   # read special section for config
    
    return time, mass, density, position, velocity, color


def save_system(path, time, mass, density, position, velocity, color):
    """Save system to file"""
    config = ConfigParser()   # load config class
    config.read(path)   # load system
    
    config.add_section("config")   # special section for config
    config.set("config", "time", str(time))   # config parameters
    
    for body, body_mass in enumerate(mass):   # for each body:
        body_name = "body" + str(body)   # generate new unique name
        config.add_section(body_name)   # add body
        config.set(body_name, "mass", str(body_mass))   # add body parameters
        config.set(body_name, "density", str(density[body]))
        config.set(body_name, "position", '[' + str(position[body, 0]) + ', ' + str(position[body, 1]) + ']')
        config.set(body_name, "velocity", '[' + str(velocity[body, 0]) + ', ' + str(velocity[body, 1]) + ']')
        config.set(body_name, "color", '[' + str(color[body, 0]) + ', ' + str(color[body, 1]) + ', ' + str(color[body, 2]) + ']')
    
    with open(path, 'w') as file:
        config.write(file)


def load_settings(header, key):
    """load one or multiple settings from same header in settings file, key must be str, tuple or list"""
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
    return setting


def save_settings(header, setting, value):
    """Saves value of specified setting to settings file"""
    settings.set(header, setting, str(value))   # config parameters
    with open("settings.ini", "w") as file:
        settings.write(file)
