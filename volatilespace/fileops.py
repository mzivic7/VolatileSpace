import tkinter as tk
from tkinter import filedialog
import numpy as np
from configparser import ConfigParser

def load_system(path):
    system = ConfigParser()   # load config class
    system.read(path)   # load system
    
    mass = np.array([])  # mass
    density = np.array([])  # density
    position = np.empty((0, 2), int)   # position
    velocity = np.empty((0, 2), int)   # velocity
    color = np.empty((0, 3), int)   # color
    
    
    for body in system.sections():   # for each body:
        if body != 'config':
            mass = np.append(mass, float(system.get(body, 'mass')))   # load all body parameters into separate arrays
            density = np.append(density, float(system.get(body, 'density')))
            position = np.vstack((position, list(map(float, system.get(body, 'position').strip('][').split(', ')))))
            velocity = np.vstack((velocity, list(map(float, system.get(body, 'velocity').strip('][').split(', ')))))
            color = np.vstack((color, list(map(int, system.get(body, 'color').strip('][').split(', ')))))
        if body == 'config':
            time = float(system.get(body, 'time'))   # read special section for config
    
    return  time, mass, density, position, velocity, color

def save_system(path, time, mass, density, position, velocity, color):
    config = ConfigParser()   # load config class
    config.read(path)   # load system
    
    config.add_section('config')   # special section for config
    config.set('config', 'time', str(time))   # config parameters
    
    for body, body_mass in enumerate(mass):   # for each body:
        body_name = "body" + str(body)   # generate new unique name
        config.add_section(body_name)   # add body
        config.set(body_name, 'mass', str(body_mass))   # add body parameters
        config.set(body_name, 'density', str(density[body]))
        config.set(body_name, 'position', '[' + str(position[body, 0]) + ', ' + str(position[body, 1]) + ']')
        config.set(body_name, 'velocity', '[' + str(velocity[body, 0]) + ', ' + str(velocity[body, 1]) + ']')
        config.set(body_name, 'color', '[' + str(color[body, 0]) + ', ' + str(color[body, 1]) + ', ' + str(color[body, 2]) + ']')
    
    with open(path, 'w') as file:   # open file at path
        config.write(file)   # save file

# save file with save dialog
def save_file(file_path):
    root = tk.Tk()   # define tkinter root
    root.withdraw()   # make tkinter root invisible
    if file_path == "": 
        file_path = "New_system.ini"
    save_file = filedialog.asksaveasfile(mode='w', initialfile = file_path, defaultextension=".txt",
                                filetypes=[("All Files","*.*"),("Text Documents","*.txt")])
    if save_file is None:   # asksaveasfile return "None" if dialog closed with "cancel"
        return ""
    file_path = save_file.name   # get path
    return file_path
    
# load file with load dialog
def load_file():
    root = tk.Tk()   # define tkinter root
    root.withdraw()   # make tkinter root invisible
    file_path = filedialog.askopenfilename()   # open load file dialog and get path
    try:   # just try to open file to see if it exists
        with open(file_path) as file:
            text = file.read()   # load all text from file
    except:   # if cant open file
        print("Error: File not found")
        file_path = ""
    return file_path
