import pygame
import math
import numpy as np
import os
import sys
import time
import datetime
from configparser import ConfigParser
from ast import literal_eval as leval
import copy
from itertools import repeat

from volatilespace import fileops
from volatilespace import physics_game
from volatilespace import physics_convert
from volatilespace.graphics import rgb
from volatilespace.graphics import graphics
from volatilespace.graphics import bg_stars
from volatilespace import textinput
from volatilespace import metric
from volatilespace import defaults


physics = physics_game.Physics()
graphics = graphics.Graphics()
bg_stars = bg_stars.Bg_Stars()
textinput = textinput.Textinput()


buttons_pause_menu = ["Resume",
                      "Save game",
                      "Load game",
                      "Settings",
                      "Quit without saving",
                      "Save and Quit"]
buttons_save = ["Cancel", "Save", "New save"]
buttons_load = ["Cancel", "Load"]
buttons_new_game = ["Cancel", "Create"]
body_types = ["Moon", "Solid planet", "Gas planet", "Star", "Black Hole"]
text_data_orb = ["Selected body: ",
                 "Parent body: ",
                 "Periapsis: ",
                 "Apoapsis: ",
                 "Eccentricity: ",
                 "Argument of Pe: ",
                 "Mean anomaly: ",
                 "True anomaly: ",
                 "Direction: ",
                 "Distance: ",
                 "Orbital Period: ",
                 "Orbital Speed: ",
                 "Horizontal Speed: ",
                 "Vertical Speed: "]
text_data_body = ["Body name: ", "Type: ", "Mass: ", "Density: ", "Radius: ", "COI altitude: "]
text_data_planet = ["(Rotation period): ",
                    "Color: ",
                    "(Atmosphere amount): ",
                    "(Atmosphere height): ",
                    "(surface gravity): "]
text_data_star = ["(Surface temp):",
                  "(Luminosity): ",
                  "Color: ",
                  "(H/He ratio): "]
text_data_bh = ["Schwarzschild radius: "]


class Game():
    def __init__(self):
        self.state = 3
        self.sim_name = "Unknown"
        self.screen_mode = False   # trigger to change screen mode
        self.screenshot = False
        
        # menu related
        self.ask = None
        self.pause_menu = False
        self.disable_input = False
        self.allow_keys = False   # allow keys when disable_input is True
        self.disable_ui = False
        self.disable_labels = False
        self.menu = None
        self.right_menu = None
        self.new_game = False
        self.text = ""
        self.click = False
        self.first_click = None
        self.click_timer = 0
        self.scroll = 0   # scroll for menus
        self.scroll_sens = 10   # scroll sensitivity
        self.scrollbar_drag = False
        self.selected_item = 0
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.fontsm = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 10)   # small text font
        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.btn_w_h_3 = (self.btn_w_l + 16)/3   # fits 3 btn in width of list button
        self.btn_w_h_2 = (self.btn_w_l + 16)/2  # fits 2 btn in width of list button
        self.txt_y_margin = 8  # empty space between text and button edge
        self.btn_h = self.fontbt.get_height() + self.txt_y_margin * 2   # button height from font height
        self.btn_s = 36   # small square button
        self.space = 10   # space between buttons
        self.file_path = ""   # path to currently active file
        self.selected_path = ""   # path to selected file
        self.input_value = None   # which value is being text-inputed
        self.new_value_raw = ""   # when inputting new value
        self.edited_orbit = False   # if orbit is edited, on first click call kepler_inverse, but don't on next clicks
        self.gen_game_list()
        self.reload_settings()
        graphics.antial = self.antial
        
        # simulation related
        self.ptps = 59   # divisor to convert simulation time to real time (it is not 60 because userevent timer is rounded to 17ms)
        self.zoom = 0.15   # initial zoom value
        self.select_sens = 5   # how many pixels are tolerable for mouse to move while selecting body
        self.drag_sens = 0.02   # drag sensitivity when inserting body
        self.warp_range = [1, 2, 3, 4, 5, 10, 50, 100]   # all possible warps, by order
        self.warp_index = 0   # current warp from warp_range
        self.sim_time = 0   # simulation time
        self.pause = False   # program paused
        self.move = False    # move view mode
        self.selected = None   # selected body
        self.dr = None   # keyboard buttons wasd
        self.follow = False   # follow selected body
        self.first = True   # is this first iteration
        self.mouse = [0, 0]   # mouse position in simulation
        self.mouse_raw = [0, 0]   # mouse position on screen
        self.mouse_raw_old = [0, 0]
        self.zoom_x, self.zoom_y = 0, 0   # initial zoom offset
        self.offset_x = self.screen_x / 2   # initial centered offset to 0, 0 coordinates
        self.offset_y = self.screen_y / 2
        self.mouse_fix_x = False   # fix mouse movement when jumping off screen edge
        self.mouse_fix_y = False
        self.zoom_step = 0.05   # initial zoom step
        self.warp = self.warp_range[self.warp_index]   # load current warp
        self.orbit_data_menu = []   # additional data for right_menu when body is selected
        self.pos = np.array([])
        self.ma = np.array([])
        self.curves = np.array([])
        
        
        self.offset_old = np.array([self.offset_x, self.offset_y])
        self.grid_enable = False   # background grid
        self.grid_mode = 0   # grid mode: 0 - global, 1 - selected body, 2 - parent
        
        
        # icons
        menu_img = pygame.image.load("img/menu.png")
        body_list_img = pygame.image.load("img/body_list.png")
        orbit_img = pygame.image.load("img/orbit.png")
        body_img = pygame.image.load("img/body.png")
        self.ui_imgs = [menu_img, body_list_img, orbit_img, body_img]
        body_moon = pygame.image.load("img/moon.png")
        body_planet_solid = pygame.image.load("img/planet_solid.png")
        body_planet_gas = pygame.image.load("img/planet_gas.png")
        body_star = pygame.image.load("img/star.png")
        body_bh = pygame.image.load("img/bh.png")
        self.body_imgs = [body_moon, body_planet_solid, body_planet_gas, body_star, body_bh]
        
        bg_stars.set_screen()   # load pygame stuff in classes after pygame init has finished
        graphics.set_screen()
    
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        self.ask_x = self.screen_x/2 - (2*self.btn_w_h + self.space)/2
        self.ask_y = self.screen_y/2 + self.space
        self.pause_x = self.screen_x/2 - self.btn_w/2
        self.pause_y = self.screen_y/2 - (len(buttons_pause_menu) * self.btn_h + (len(buttons_pause_menu)-1) * self.space)/2
        self.pause_max_y = self.btn_h*len(buttons_pause_menu) + self.space*(len(buttons_pause_menu)+1)
        self.games_x = self.screen_x/2 - self.btn_w_l/2
        self.games_max_y = self.screen_y - 200
        self.list_limit = self.games_max_y - self.btn_h - self.space
        self.games_y = (self.screen_y - self.games_max_y)/2
        self.games_x_ui = self.games_x - self.space
        self.games_y_ui = self.games_y + self.list_limit + self.space
        self.game_list_size = len(self.games) * self.btn_h + len(self.games) * self.space
        self.right_menu_x = self.screen_x - 300
        self.r_menu_limit = self.screen_y - 38 - self.space
        self.r_menu_x_btn = self.right_menu_x + self.space
    
    
    def reload_settings(self):
        """Reload all settings for editor and graphics, should be run every time editor is entered"""
        self.fullscreen = leval(fileops.load_settings("graphics", "fullscreen"))
        avail_res = pygame.display.list_modes()
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        try:
            self.selected_res = avail_res.index((self.screen_x, self.screen_y))
        except Exception:   # fail-safe repair if resolution is invalid
            self.selected_res = 0   # use maximum resolution
            fileops.save_settings("graphics", "resolution", list(avail_res[0]))   # save it to file
            if self.fullscreen:
                pygame.display.set_mode((avail_res[0]), pygame.FULLSCREEN)
            else:
                pygame.display.set_mode((avail_res[0]))
        self.antial = leval(fileops.load_settings("graphics", "antialiasing"))
        self.mouse_wrap = leval(fileops.load_settings("graphics", "mouse_wrap"))
        self.bg_stars_enable = leval(fileops.load_settings("background", "stars"))
        bg_stars.reload_settings()
        graphics.reload_settings()
        physics.reload_settings()
        self.set_screen()   # resolution may have been changed
        bg_stars.set_screen()
        graphics.set_screen()
        self.keys = fileops.load_keybindings()
        self.right_menu = None
        self.autosave_event = pygame.USEREVENT + 1
        autosave_time = int(fileops.load_settings("game", "autosave_time")) * 60 * 1000   # min to ms
        pygame.time.set_timer(self.autosave_event, autosave_time)
    
    
    def gen_game_list(self):
        self.games = fileops.gen_game_list()
        self.game_list_size = len(self.games) * self.btn_h + len(self.games) * self.space
        if len(self.games) != 0:
            self.selected_path = "Saves/" + self.games[self.selected_item, 0]
        
        # limit text size
        for num, text in enumerate(self.games[:, 1]):
            new_text = graphics.limit_text(text, self.fontbt, self.btn_w_l)
            if new_text != text:
                self.games[num, 1] = new_text
        
        # find selected item based on currently active file
        selected_item = np.where(self.games[:, 0] == self.file_path.strip("Saves/"))[0]
        if len(selected_item) == 0:
            self.selected_item = 0
        else:
            self.selected_item = selected_item[0]
            self.selected_path = "Saves/" + self.games[self.selected_item, 0]
    
    
    def load_system(self, system):
        self.sim_name, self.sim_time, self.sim_conf, self.names, self.mass, self.density, self.color, orb_data = fileops.load_file(system)
        self.sim_time *= self.ptps   # convert from seconds to userevent iterations
        if not orb_data["kepler"]:   # convert to keplerian model
            coi_coef = self.sim_conf["coi_coef"]
            gc = self.sim_conf["gc"]
            orb_data = physics_convert.to_kepler(self.mass, orb_data, gc, coi_coef)
            os.remove(system)
            date = time.strftime("%d.%m.%Y %H:%M")
            fileops.save_file(system, self.sim_name, date, self.sim_conf, self.sim_time/self.ptps,
                              self.names, self.mass, self.density, self.color, orb_data)
        
        physics.load_system(self.sim_conf, self.names, self.mass, self.density, self.color, orb_data)
        self.file_path = system   # this path will be used for load/save
        self.disable_input = False
        self.disable_ui = False
        self.disable_labels = False
        self.gen_game_list()
        self.selected_item = 0
        self.selected = None
        self.warp_index = 0
        self.warp = 1
        self.first = True
        
        # userevent may not been run in first iteration, but this values are needed in graphics section:
        body_data, body_orb = physics.body()
        self.unpack_body(body_data, body_orb)
        self.pos, self.ma = physics.body_move(self.warp)
        physics.body_curve()
        self.curves = physics.body_curve_move()
        self.first = True
    
    
    ###### --Help functions-- ######
    def focus_point(self, pos, zoom=None):
        """Claculate offset and zoom, used to focus on specific coordinates"""
        if zoom:
            self.zoom = zoom
        self.offset_x = - pos[0] + self.screen_x / 2   # follow selected body
        self.offset_y = - pos[1] + self.screen_y / 2
        self.zoom_x = (self.screen_x / 2) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
        self.zoom_y = (self.screen_y / 2) - (self.screen_y / (self.zoom * 2))

    def screen_coords(self, coords_in_sim):
        """Converts from sim coords to screen coords. Adds zoom, view move, and moves origin from up-left to bottom-left"""
        x_on_screen = (coords_in_sim[0] + self.offset_x - self.zoom_x) * self.zoom   # correction for zoom, screen movement offset
        y_on_screen = (coords_in_sim[1] + self.offset_y - self.zoom_y) * self.zoom
        y_on_screen = self.screen_y - y_on_screen   # move origin from up-left to bottom-left
        return np.array([x_on_screen, y_on_screen])
    
    def sim_coords(self, coords_on_screen):
        """Converts from screen coords to sim coords. Adds zoom, view move, and moves origin from bottom-left to up-left"""
        x_in_sim = coords_on_screen[0] / self.zoom - self.offset_x + self.zoom_x   # correction for zoom, screen movement offset
        y_in_sim = -(coords_on_screen[1] - self.screen_y) / self.zoom - self.offset_y + self.zoom_y
        # y_on_screen = y_on_screen - screen_y   move origin from bottom-left to up-left. This is implemented in above line
        return [x_in_sim, y_in_sim]
    
    
    def unpack_body(self, body_data, body_orb):
        """Unpacks values from dict and stores them in class variables. Reading dict values is slower than variable."""
        # BODY DATA #
        self.names = body_data["name"]
        self.types = body_data["type"]
        self.mass = body_data["mass"]
        self.density = body_data["den"]
        self.temp = body_data["temp"]
        self.base_color = body_data["color_b"]
        self.color = body_data["color"]
        self.size = body_data["size"]
        self.rad_sc = body_data["rad_sc"]
        # ORBIT DATA #
        self.a = body_orb["a"]
        self.b = body_orb["b"]
        self.f = body_orb["f"]
        self.coi = body_orb["coi"]
        self.ref = body_orb["ref"]
        self.ecc = body_orb["ecc"]
        self.pe_d = body_orb["pe_d"]
        self.ap_d = body_orb["ap_d"]
        self.pea = body_orb["pea"]
        self.dr = body_orb["dir"]
        self.period = body_orb["per"]
    
    
    def load(self):
        """Loads system from "load" dialog."""
        if os.path.exists(self.selected_path):
            self.load_system(self.selected_path)
            body_data, body_orb = physics.body()
            self.unpack_body(body_data, body_orb)
            self.pos, self.ma = physics.body_move(self.warp)
            physics.body_curve()
            self.curves = physics.body_curve_move()
            self.file_path = self.selected_path   # change currently active file
            graphics.timed_text_init(rgb.gray, self.fontmd, "Map loaded successfully", (self.screen_x/2, self.screen_y-70), 2, True)
        
    def save(self, path, name=None, silent=False):
        """Saves game to file. If name is None, name is not changed."""
        date = time.strftime("%d.%m.%Y %H:%M")
        orb_data = {"a": self.a, "ecc": self.ecc, "pe_arg": self.pea, "ma": self.ma, "ref": self.ref, "dir": self.dr}
        fileops.save_file(path, name, date, self.sim_conf, self.sim_time/self.ptps,
                          self.names, self.mass, self.density, self.base_color, orb_data)
        if not silent:
            graphics.timed_text_init(rgb.gray, self.fontmd, "Map saved successfully", (self.screen_x/2, self.screen_y-70), 2, True)
    
    def quicksave(self):
        """Saves game to quicksave file."""
        date = time.strftime("%d.%m.%Y %H:%M")
        orb_data = {"a": self.a, "ecc": self.ecc, "pe_arg": self.pea, "ma": self.ma, "ref": self.ref, "dir": self.dr}
        fileops.save_file("Saves/quicksave.ini", "Quicksave - " + self.sim_name, date, self.sim_conf, self.sim_time/self.ptps,
                          self.names, self.mass, self.density, self.base_color, orb_data)
        graphics.timed_text_init(rgb.gray2, self.fontmd, "Quicksave...", (self.screen_x/2, self.screen_y-70), 2, True)
    
    def autosave(self, e):
        """Automatically saves current game to autosave.ini at predefined interval."""
        if e.type == self.autosave_event:
            date = time.strftime("%d.%m.%Y %H:%M")
            orb_data = {"a": self.a, "ecc": self.ecc, "pe_arg": self.pea, "ma": self.ma, "ref": self.ref, "dir": self.dr}
            fileops.save_file("Saves/autosave.ini", "Autosave - " + self.sim_name, date, self.sim_conf, self.sim_time/self.ptps,
                              self.names, self.mass, self.density, self.base_color, orb_data)
            graphics.timed_text_init(rgb.gray2, self.fontmd, "Autosave...", (self.screen_x/2, self.screen_y-70), 2, True)

    
    
    
    ###### --Keys-- ######
    def input_keys(self, e):
        if self.state != 2:   # when returning to editor menu
            self.state = 2   # update state
        
        # new game menu
        if self.new_game:
            self.text = textinput.input(e)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.new_game = False
                    self.ask = None
                elif e.key == pygame.K_RETURN:
                    date = time.strftime("%d.%m.%Y %H:%M")
                    path = fileops.new_game(self.text, date)
                    self.save(path)
                    self.gen_game_list()
                    self.new_game = False
                    self.ask = None
        
        # save and load menu
        elif self.menu == 0 or self.menu == 1:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.scrollbar_drag:
                        self.scrollbar_drag = False
                    elif self.ask:
                        self.ask = None
                    else:
                        self.menu = None
                        self.pause_menu = True
                if e.key == pygame.K_RETURN:
                    if self.ask:
                        if self.ask == "load":
                            self.load()
                        if self.ask == "save":
                            self.save(self.selected_path)
                            self.file_path = self.selected_path
                        self.menu = None
                        self.pause_menu = True
                        self.ask = None
                    if self.menu == 0:
                        self.ask = "save"
                    elif self.menu == 1:
                        self.ask = "load"
                if not self.ask:
                    if e.key == pygame.K_DOWN:
                        if self.selected_item < len(self.games)-1:
                            self.selected_item += 1
                            self.selected_path = "Saves/" + self.games[self.selected_item, 0]
                    elif e.key == pygame.K_UP:
                        if self.selected_item > 0:
                            self.selected_item -= 1
                            self.selected_path = "Saves/" + self.games[self.selected_item, 0]
        
        # in game
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.ask is None:
                    if self.pause_menu:
                        self.pause_menu = False
                        self.disable_input = False
                        self.pause = False
                    else:
                        self.pause_menu = True
                        self.disable_input = True
                        self.pause = True
                else:   # exit from ask window
                    self.ask = None
                    self.disable_input = False
            
            if not self.disable_input or self.allow_keys:
                if e.key == self.keys["interactive_pause"]:
                    if self.pause is False:
                        self.pause = True   # if not paused, pause it
                    else:
                        self.pause = False  # if paused, unpause it
                
                elif e.key == self.keys["focus_home"]:
                    self.follow = False   # disable follow
                    self.focus_point([0, 0], self.zoom)   # return to (0,0) coordinates
                    
                elif e.key == self.keys["follow_selected_body"]:
                    self.follow = not self.follow   # toggle follow
                
                elif e.key == self.keys["toggle_background_grid"]:
                    self.grid_enable = not self.grid_enable
                
                elif e.key == self.keys["cycle_grid_modes"]:
                    if self.grid_enable:
                        self.grid_mode += 1   # cycle grid modes (0 - global, 1 - selected body, 2 - parent)
                        if self.grid_mode >= 3:
                            self.grid_mode = 0
                
                elif e.key == self.keys["screenshot"]:
                    if not os.path.exists("Screenshots"):
                        os.mkdir("Screenshots")
                    self.screenshot = True
                
                elif e.key == self.keys["toggle_ui_visibility"]:
                    self.disable_ui = not self.disable_ui
                
                elif e.key == self.keys["toggle_labels_visibility"]:
                    self.disable_labels = not self.disable_labels
                
                elif e.key == self.keys["quicksave"]:
                    self.quicksave()
                
                
                # time warp
                if e.key == self.keys["decrease_time_warp"]:
                    if self.warp_index != 0:   # stop index from going out of range
                        self.warp_index -= 1   # decrease warp index
                    self.warp = self.warp_range[self.warp_index]   # update warp
                if e.key == self.keys["increase_time_warp"]:
                    if self.warp_index != len(self.warp_range)-1:   # stop index from going out of range
                        self.warp_index += 1   # increase warp index
                    self.warp = self.warp_range[self.warp_index]   # update warp
                if e.key == self.keys["stop_time_warp"]:
                    self.warp_index = 0   # reset warp index
                    self.warp = self.warp_range[self.warp_index]   # update warp
    
    
    
    ###### --Simulation Mouse-- ######
    def input_mouse(self, e):
        self.mouse_raw = list(pygame.mouse.get_pos())   # get mouse position
        self.mouse = list((self.mouse_raw[0]/self.zoom, -(self.mouse_raw[1] - self.screen_y)/self.zoom))   # mouse position on zoomed screen
        # y coordinate in self.mouse is negative for easier applying in formula to check if mouse is inside circle
        
        # disable input when mouse clicks on ui
        if not self.pause_menu and self.menu is None:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.mouse_raw[0] <= self.btn_s or self.mouse_raw[1] <= 22:
                    if self.disable_ui is False:
                        self.disable_input = True
                        self.allow_keys = True
                else:
                    self.disable_input = False
                    self.allow_keys = False
                if self.right_menu is not None:
                    if self.disable_ui is False:
                        if self.mouse_raw[0] >= self.right_menu_x:
                            self.disable_input = True
                            self.allow_keys = True
        
        if not self.disable_input:
            # moving and selecting with lclick
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    self.move = True   # enable view move
                    self.mouse_old = self.mouse   # initial mouse position for movement
                    self.mouse_raw_old = self.mouse_raw   # initial mouse position for movement
                    
            if e.type == pygame.MOUSEBUTTONUP:
                if e.button == 1:
                    self.move = False   # disable move
                    mouse_move = math.dist(self.mouse_raw, self.mouse_raw_old)   # mouse move dist
                    self.select_toggle = False
                    if e.button != 2:   # don't select body with middle click when in insert mode
                        if mouse_move < self.select_sens:   # if mouse moved less than n pixels:
                            for body, body_pos in enumerate(self.pos):   # for each body:
                                curve = np.column_stack(self.screen_coords(self.curves[:, body]))   # get line coords on screen
                                diff = np.amax(curve, 0) - np.amin(curve, 0)
                                if body == 0 or diff[0]+diff[1] > 32:   # skip hidden bodies with too small orbits
                                    scr_radius = self.size[body]*self.zoom
                                    if scr_radius < 5:   # if body is small on screen, there is marker
                                        scr_radius = 8
                                    # if mouse is inside body radius on its location: (body_x - mouse_x)**2 + (body_y - mouse_y)**2 < radius**2
                                    if sum(np.square(self.screen_coords(body_pos) - self.mouse_raw)) < (scr_radius)**2:
                                        self.selected = body  # this body is selected
                                        self.select_toggle = True   # do not exit select mode
                            if self.select_toggle is False and self.right_menu not in [3, 4]:   # if inside select mode and not in data right menus
                                self.selected = None   # exit select mode
                                if self.right_menu in [3, 4]:
                                    self.right_menu = None   # disable orbit and body data
            
            
            # mouse wheel: change zoom
            if not self.disable_input:
                if e.type == pygame.MOUSEWHEEL:   # change zoom
                    if self.zoom > self.zoom_step or e.y == 1:   # prevent zooming below zoom_step, zoom can't be 0, but allow zoom to increase
                        self.zoom_step = self.zoom / 10   # calculate zoom_step from current zoom
                        self.zoom += e.y * self.zoom_step   # add value to zoom by scrolling on mouse
                        self.zoom_x += (self.screen_x / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
                        self.zoom_y += (self.screen_y / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_y / (self.zoom * 2))
                        # these values are added only to displayed objects, traces... But not to real position
    
    
    
    ###### --UI Mouse-- ######
    def ui_mouse(self, e):
        btn_disable_input = False
        if self.disable_input and not self.allow_keys:
            btn_disable_input = True
        graphics.update_mouse(self.mouse_raw, self.click, btn_disable_input)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click = True
            
            # scroll bar
            if self.menu == 0 or self.menu == 1:
                scrollable_len = max(0, self.game_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                if scrollable_len != 0:
                    scrollbar_pos = self.scroll * scrollbar_limit / scrollable_len
                else:
                    scrollbar_pos = 0
                scrollbar_x = self.games_x + self.btn_w_l + self.space + 2    # calculate scroll bar coords
                scrollbar_y = self.games_y - self.space + 3 + scrollbar_pos
                if scrollbar_x <= self.mouse_raw[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse_raw[1]-1 <= scrollbar_y + 40:
                    self.scrollbar_drag = True
                    self.scrollbar_drag_start = self.mouse[1]
                    self.ask = True   # dirty shortcut to disable safe buttons
        
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.click:
                
                # pause menu
                if self.pause_menu:
                    y_pos = self.pause_y
                    for num, text in enumerate(buttons_pause_menu):
                        if self.pause_x <= self.mouse_raw[0]-1 <= self.pause_x + self.btn_w and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # resume
                                self.pause_menu = False
                                self.disable_input = False
                                self.pause = False
                            elif num == 1:   # save
                                self.menu = 0
                                self.pause_menu = False
                                self.gen_game_list()
                            elif num == 2:   # load
                                self.menu = 1
                                self.pause_menu = False
                                self.gen_game_list()
                            elif num == 3:   # settings
                                self.state = 4   # go directly to main menu settings, but be able to return here
                            elif num == 4:   # quit
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.pause = False
                            elif num == 5:   # save and quit
                                self.save(self, self.file_path, name=self.sim_name, silent=True)
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.pause = False
                        y_pos += self.btn_h + self.space
                
                # disable scrollbar_drag when release click
                elif self.scrollbar_drag:
                    self.scrollbar_drag = False
                    self.ask = None
                
                # save
                elif self.menu == 0:
                    # new game
                    if self.new_game:
                        x_pos = self.ask_x
                        for num in [0, 1]:
                            if x_pos <= self.mouse_raw[0]-1 <= x_pos+self.btn_w_h and self.ask_y+self.space <= self.mouse_raw[1]-1 <= self.ask_y+self.space+self.btn_h:
                                if num == 0:   # cancel
                                    pass
                                elif num == 1:   # save
                                    path = fileops.new_game(self.text, time.strftime("%d.%m.%Y %H:%M"))
                                    self.save(path, name=self.text)
                                    self.gen_game_list()
                                self.new_game = False
                                self.ask = None
                            x_pos += self.btn_w_h + self.space
                    
                    else:   # disables underlaying menu
                        # games list
                        if self.games_y - self.space <= self.mouse_raw[1]-1 <= self.games_y + self.list_limit:
                            y_pos = self.games_y - self.scroll
                            for num, text in enumerate(self.games[:, 1]):
                                if y_pos >= self.games_y - self.btn_h - self.space and y_pos <= self.games_y + self.list_limit:    # don't detect outside list area
                                    if self.games_x <= self.mouse_raw[0]-1 <= self.games_x + self.btn_w_l and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                                        self.selected_item = num
                                        self.selected_path = "Saves/" + self.games[self.selected_item, 0]
                                        if self.first_click == num:   # detect double click
                                            if self.file_path == self.selected_path:   # don't ask to save over current file
                                                self.save(self.file_path)
                                                self.menu = None
                                                self.pause_menu = True
                                            else:
                                                self.ask = "save"
                                            self.click = False   # dont carry click to ask window
                                        self.first_click = num
                                y_pos += self.btn_h + self.space
                        
                        # ui
                        x_pos = self.games_x_ui
                        for num, text in enumerate(buttons_save):
                            if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h_3 and self.games_y_ui <= self.mouse_raw[1]-1 <= self.games_y_ui + self.btn_h:
                                if num == 0:   # cancel
                                    self.menu = None
                                    self.pause_menu = True
                                elif num == 1:   # save
                                    if self.file_path == self.selected_path:   # don't ask to save over current file
                                        self.save(self.file_path)
                                        self.menu = None
                                        self.pause_menu = True
                                    else:
                                        self.ask = "save"
                                elif num == 2:   # new save
                                    self.new_game = True
                                    self.ask = True   # dirty shortcut to disable safe buttons
                            x_pos += self.btn_w_h_3 + self.space
                
                # load
                elif self.menu == 1:
                    # games list
                    if self.games_y - self.space <= self.mouse_raw[1]-1 <= self.games_y + self.list_limit:
                        y_pos = self.games_y - self.scroll
                        for num, text in enumerate(self.games[:, 1]):
                            if y_pos >= self.games_y - self.btn_h - self.space and y_pos <= self.games_y + self.list_limit:    # don't detect outside list area
                                if self.games_x <= self.mouse_raw[0]-1 <= self.games_x + self.btn_w_l and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                                    self.selected_item = num
                                    self.selected_path = "Saves/" + self.games[self.selected_item, 0]
                                    if self.first_click == num:   # detect double click
                                        self.ask = "load"
                                        self.click = False   # dont carry click to ask window
                                    self.first_click = num
                            y_pos += self.btn_h + self.space
                    
                    x_pos = self.games_x_ui
                    for num, text in enumerate(buttons_load):
                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h_2 and self.games_y_ui <= self.mouse_raw[1]-1 <= self.games_y_ui + self.btn_h:
                            if num == 0:   # cancel
                                self.menu = None
                                self.pause_menu = True
                            elif num == 1:   # save
                                self.ask = "load"
                        x_pos += self.btn_w_h_2 + self.space
                
                # settings
                elif self.menu == 2:
                    pass
            
            # ask
            if self.click:
                if self.ask is not None:
                    x_pos = self.ask_x
                    for num in [0, 1]:
                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h and self.ask_y <= self.mouse_raw[1]-1 <= self.ask_y + self.btn_h:
                            if num == 0:   # cancel
                                pass
                            elif num == 1:   # yes
                                if self.ask == "load":
                                    self.load()
                                if self.ask == "save":
                                    self.save(self.selected_path)
                                    self.file_path = self.selected_path
                            self.menu = None
                            self.pause_menu = True
                            self.ask = None
                        x_pos += self.btn_w_h + self.space
            
            if not self.disable_ui:
                # left ui
                if not self.input_value:   # don't change window if textinpt is active
                    y_pos = 23
                    for num, img in enumerate(self.ui_imgs):
                        if 0 <= self.mouse_raw[0] <= 0 + self.btn_s and y_pos <= self.mouse_raw[1] <= y_pos + self.btn_s:
                            if num == 0:   # menu
                                self.pause_menu = True
                                self.disable_input = True
                                self.pause = True
                                self.right_menu = None
                            else:
                                if self.right_menu == num:
                                    self.right_menu = None
                                else:
                                    if num in [2, 3]:
                                        if self.selected is not None:
                                            if num == 2 and self.selected == self.ref[self.selected]:   # don't display orbit edit for root body
                                                pass
                                            else:
                                                self.right_menu = num
                                                self.click = False
                                    else:
                                        self.right_menu = num
                        y_pos += self.btn_s + 1
            
            # right ui
                if not self.click_timer:
                    if self.right_menu == 1:   # body list
                        y_pos = 38
                        for num, name in enumerate(self.names):
                            if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                self.selected = num
                                self.follow = True
                            y_pos += 26
            
            # scrollbar
            if e.type == pygame.MOUSEWHEEL and (self.menu == 0 or self.menu == 1):
                if self.scrollbar_drag is False:
                    # scrolling inside list area
                    if self.games_x-self.space <= self.mouse_raw[0]-1 <= self.games_x+self.btn_w_l+self.space+16 and self.games_y-self.space <= self.mouse_raw[1]-1 <= self.games_y+self.list_limit:
                        self.scroll -= e.y * self.scroll_sens
                        if self.scroll < 0:
                            self.scroll = 0
                        elif self.scroll > max(0, self.game_list_size - self.list_limit):
                            self.scroll = max(0, self.game_list_size - self.list_limit)
            
            self.click = False
        
        # moving scrollbar with cursor
        if self.scrollbar_drag:
            if self.menu == 0 or self.menu == 1:
                # calculate scroll from scrollbar position
                scrollbar_pos = self.mouse_raw[1] - self.games_y
                scrollable_len = max(0, self.game_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                self.scroll = scrollable_len * scrollbar_pos / scrollbar_limit
                if self.scroll < 0:
                    self.scroll = 0
                elif self.scroll > max(0, self.game_list_size - self.list_limit):
                    self.scroll = max(0, self.game_list_size - self.list_limit)
        
        return self.state
    
    
    ###### --Physics-- ######
    def physics(self, e):
        if e.type == pygame.USEREVENT:   # event for calculations
            if self.pause is False:   # if it is not paused:
                self.pos, self.ma = physics.body_move(self.warp)
                self.curves = physics.body_curve_move()
                self.sim_time += 1 * self.warp   # iterate sim_time
                
                if self.first:   # this is run only once at userevent start
                    self.first = False   # do not run it again
                    self.focus_point([0, 0], 0.5)   # initial zoom and point
                    self.selected = 0   # select body
                    self.follow = True   # follow it
    
    
    
    ###### --Graphics-- ######
    def graphics(self, screen, clock):
        screen.fill((0, 0, 0))   # color screen black
        
        
        # follow body (this must be before drawing objects to prevent them from vibrating when moving)
        if self.follow and self.selected is not None:   # if follow mode is enabled
            self.offset_x = - self.pos[self.selected, 0] + self.screen_x / 2   # follow selected body
            self.offset_y = - self.pos[self.selected, 1] + self.screen_y / 2
        
        # screen movement
        if self.move:   # this is not in userevent to allow moving while paused
            if self.mouse_fix_x:   # when mouse jumps from one edge to other:
                self.mouse_old[0] = self.mouse[0]   # don't calculate that as mouse movement
                self.mouse_fix_x = False
            if self.mouse_fix_y:
                self.mouse_old[1] = self.mouse[1]
                self.mouse_fix_y = False
            
            mouse_move = math.dist((self.mouse_raw[0], self.mouse_raw[1]), (self.mouse_raw_old[0], self.mouse_raw_old[1]))   # distance
            self.offset_x += self.mouse[0] - self.mouse_old[0]   # add mouse movement to offset
            self.offset_y += self.mouse[1] - self.mouse_old[1]
            # save mouse position for next iteration to get movement
            if mouse_move > self.select_sens:   # stop following if mouse distance is more than n pixels
                self.follow = False   # stop following selected body
            
            if self.mouse_wrap:
                if self.mouse_raw[0] >= self.screen_x-1:   # if mouse hits screen edge
                    pygame.mouse.set_pos(1, self.mouse_raw[1])   # move it to opposite edge ### BUG ###
                    self.mouse_fix_x = True   # in next itteration, dont calculate that as movement
                if self.mouse_raw[0] <= 0:
                    pygame.mouse.set_pos(self.screen_x, self.mouse_raw[1]-1)    # ### BUG ###
                    self.mouse_fix_x = True
                if self.mouse_raw[1] >= self.screen_y-1:
                    pygame.mouse.set_pos(self.mouse_raw[0], 1)    # ### BUG ###
                    self.mouse_fix_y = True
                if self.mouse_raw[1] <= 0:
                    pygame.mouse.set_pos(self.mouse_raw[0], self.screen_y-1)    # ### BUG ###
                    self.mouse_fix_y = True
            self.mouse_old = self.mouse
        
        
        # background stars:
        if self.bg_stars_enable:
            offset_diff = self.offset_old - np.array([self.offset_x, self.offset_y])   # movement vector in one iterration
            offset_diff = offset_diff * min(self.zoom, 3)   # add zoom to speed calculation and limit zoom
            self.offset_old = np.array([self.offset_x, self.offset_y])
            if not self.first:
                speed = math.sqrt(offset_diff.dot(offset_diff))/3   # speed as movement vector magnitude
                while speed > 300:   # limits speed when view is jumping (focus home, distant body...)
                    speed = math.sqrt(speed)
            else:
                speed = 0
            direction = math.atan2(offset_diff[1], offset_diff[0])   # movement vector angle from atan2
            bg_stars.draw_bg(screen, speed, direction, self.zoom)
        
        
        # background lines grid
        if self.grid_enable:
            if self.grid_mode == 0:   # grid mode: home
                origin = self.screen_coords([0, 0])
            if self.selected is not None:
                if self.grid_mode == 1:      # grid mode: selected body
                    if self.follow is False:
                        origin = self.screen_coords(self.pos[self.selected])
                    else:   # When following body, origin is in center of screen
                        origin = [(- self.zoom_x + self.screen_x/2) * self.zoom, self.screen_y - (- self.zoom_y + self.screen_y/2) * self.zoom]
                if self.grid_mode == 2:   # grid mode: parent of selected body
                    origin = self.screen_coords(self.pos[self.ref[self.selected]])
            else:
                origin = self.screen_coords([0, 0])
            graphics.draw_grid(screen, self.grid_mode, origin, self.zoom)
        
        
        # bodies drawing
        for body in range(len(self.mass)):   # for each body:
            curve = np.column_stack(self.screen_coords(self.curves[:, body]))   # get line coords on screen
            diff = np.amax(curve, 0) - np.amin(curve, 0)
            if body == 0 or diff[0]+diff[1] > 32:   # skip bodies with too small orbits
                
                # draw orbit curve lines
                if body != 0:   # skip root
                    line_color = np.where(self.color[body] > 255, 255, self.color[body])   # get line color and limit values to top 255
                    graphics.draw_lines(screen, tuple(line_color), curve, 2)   # draw that line
                
                # draw bodies
                scr_body_size = self.size[body] * self.zoom   # get body screen size
                body_color = tuple(self.color[body])   # get color
                if scr_body_size >= 5:
                    graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.pos[body]), scr_body_size)
                else:   # if body is too small, draw marker with fixed size
                    graphics.draw_circle_fill(screen, rgb.gray1, self.screen_coords(self.pos[body]), 6)
                    graphics.draw_circle_fill(screen, rgb.gray2, self.screen_coords(self.pos[body]), 5)
                    graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.pos[body]), 4)
                
                # select body
                if self.selected is not None and self.selected == body:
                    parent = self.ref[body]      # get selected body parent
                    body_pos = self.pos[body, :]      # get selected body position
                    ta, pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert = physics.body_selected(self.selected)
                    if self.right_menu == 2:
                        self.orbit_data_menu = [self.pe_d[self.selected],
                                                self.ap_d[self.selected],
                                                self.ecc[self.selected],
                                                self.pea[self.selected] * 180 / np.pi,
                                                self.ma[self.selected] * 180 / np.pi,
                                                ta * 180 / np.pi,
                                                self.dr[self.selected],
                                                distance,
                                                self.period[self.selected],
                                                speed_orb,
                                                speed_hor,
                                                speed_vert]
                    
                    # circles
                    if not self.disable_labels:
                        if scr_body_size >= 5:
                            graphics.draw_circle(screen, rgb.cyan, self.screen_coords(body_pos), self.size[body] * self.zoom + 4, 2)   # selection circle
                        else:
                            graphics.draw_circle(screen, rgb.cyan, self.screen_coords(body_pos), 8, 2)   # for body marker
                        if self.size[body] < self.coi[body]:
                            if self.coi[body] * self.zoom >= 8:
                                graphics.draw_circle(screen, rgb.gray1, self.screen_coords(body_pos), self.coi[body] * self.zoom, 1)   # circle of influence
                        if body != 0:
                            parent_scr = self.screen_coords(self.pos[parent])
                            if self.size[parent] * self.zoom >= 5:
                                graphics.draw_circle(screen, rgb.red1, parent_scr, self.size[parent] * self.zoom + 4, 1)   # parent circle
                            else:
                                graphics.draw_circle(screen, rgb.red1, parent_scr, 8, 1)   # for body marker
                            if parent != 0:
                                if self.coi[parent] * self.zoom >= 8:
                                    graphics.draw_circle(screen, rgb.red1, parent_scr, self.coi[parent] * self.zoom, 1)   # parent circle of influence
                            
                            # ap and pe
                            if self.ap_d[body] > 0:
                                ap_scr = self.screen_coords(ap)   # apoapsis with zoom and offset
                            else:   # in case of hyperbola/parabola (ap_d is negative)
                                ap_scr = self.screen_coords(pe)
                            scr_dist = abs(parent_scr - ap_scr)
                            if scr_dist[0] > 5 or scr_dist[1] > 5:   # dont draw Ap and Pe if Ap is too close to parent
                                
                                # periapsis location marker, text: distance and time to it
                                pe_scr = self.screen_coords(pe)   # periapsis screen coords
                                graphics.draw_circle_fill(screen, rgb.lime1, pe_scr, 3)   # periapsis marker
                                graphics.text(screen, rgb.lime1, self.fontsm, "Periapsis: " + str(round(self.pe_d[body], 1)), (pe_scr[0], pe_scr[1] + 7), True)
                                graphics.text(screen, rgb.lime1, self.fontsm, "T - " + str(datetime.timedelta(seconds=round(pe_t/self.ptps))), (pe_scr[0], pe_scr[1] + 17), True)
                                
                                if self.ecc[body] < 1:   # if orbit is ellipse
                                    # apoapsis location marker, text: distance and time to it
                                    graphics.draw_circle_fill(screen, rgb.lime1, ap_scr, 3)   # apoapsis marker
                                    graphics.text(screen, rgb.lime1, self.fontsm, "Apoapsis: " + str(round(self.ap_d[body], 1)), (ap_scr[0], ap_scr[1] + 7), True)
                                    graphics.text(screen, rgb.lime1, self.fontsm, "T - " + str(datetime.timedelta(seconds=round(ap_t/self.ptps))), (ap_scr[0], ap_scr[1] + 17), True)
    
    
    
    ###### --Menus-- ######
    def graphics_ui(self, screen, clock):
        
        # pause menu
        if self.pause_menu:
            border_rect = [self.pause_x-self.space, self.pause_y-self.space, self.btn_w+2*self.space, self.pause_max_y]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
            graphics.buttons_vertical(screen, buttons_pause_menu, (self.pause_x, self.pause_y), safe=True)
        
        # save menu
        if self.menu == 0:
            border_rect = [self.games_x-2*self.space, self.games_y-2*self.space, self.btn_w_l+4*self.space + 16, self.games_max_y+3*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            graphics.buttons_list(screen, self.games[:, 1], (self.games_x, self.games_y), self.list_limit, self.scroll, self.selected_item, safe=not bool(self.ask))
            graphics.buttons_horizontal(screen, buttons_save, (self.games_x_ui, self.games_y_ui), alt_width=self.btn_w_h_3, safe=not bool(self.ask))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
        
        # load menu
        elif self.menu == 1:
            border_rect = [self.games_x-2*self.space, self.games_y-2*self.space, self.btn_w_l+4*self.space + 16, self.games_max_y+3*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            graphics.buttons_list(screen, self.games[:, 1], (self.games_x, self.games_y), self.list_limit, self.scroll, self.selected_item, safe=not (bool(self.ask)))
            graphics.buttons_horizontal(screen, buttons_load, (self.games_x - self.space, self.games_y_ui), alt_width=self.btn_w_h_2, safe=not (bool(self.ask)))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
        
        # asking to load/save
        if self.ask == "load":
            ask_txt = "Loading will overwrite unsaved changes."
            graphics.ask(screen, ask_txt, self.games[self.selected_item, 1], "Load", (self.ask_x, self.ask_y))
        elif self.ask == "save":
            ask_txt = "Are you sure you want to overwrite this save:"
            graphics.ask(screen, ask_txt, self.games[self.selected_item, 1], "Save", (self.ask_x, self.ask_y))
        
        # screenshot
        if self.screenshot:
            date = time.strftime("%Y-%m-%d %H-%M-%S")
            screenshot_path = "Screenshots/Screenshot from " + date + ".png"
            pygame.image.save(screen, screenshot_path)
            if not self.disable_ui:
                graphics.timed_text_init(rgb.gray, self.fontmd, "Screenshot saved at: " + screenshot_path, (self.screen_x/2, self.screen_y-70), 2, True)
            self.screenshot = False
        
        # new game
        if self.new_game:
            border_rect = [self.ask_x-self.space, self.ask_y-40-self.btn_h, self.btn_w_h*2+3*self.space, self.btn_h+40+self.btn_h+2*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
            graphics.text(screen, rgb.white, self.fontbt, "New Map", (self.screen_x/2,  self.ask_y-20-self.btn_h), True)
            textinput.graphics(screen, clock, self.fontbt, (self.ask_x, self.ask_y-self.btn_h), (self.btn_w_h*2+self.space, self.btn_h))
            graphics.buttons_horizontal(screen, buttons_new_game, (self.ask_x, self.ask_y+self.space), safe=True)
    
        # double click counter   # not graphics related, but must be outside of input functions
        if self.first_click is not None:
            self.click_timer += clock.get_fps() / 60
            if self.click_timer >= 0.4 * 60:
                self.first_click = None
                self.click_timer = 0
        
        
        if not self.disable_ui:
            graphics.timed_text(screen, clock)   # timed text on screen
            
            # left ui
            pygame.draw.rect(screen, rgb.black, (0, 0, self.btn_s, self.screen_y))
            if self.selected is not None:
                prop_l = None
                if self.selected == self.ref[self.selected]:
                    prop_l = [None, None, 0, None]
            else:
                prop_l = [None, None, 0, 0]
            graphics.buttons_small(screen, self.ui_imgs, (0, 23), prop=prop_l, selected=self.right_menu)
            pygame.draw.line(screen, rgb.white, (self.btn_s, 0), (self.btn_s, self.screen_y), 1)
            
            # right ui
            if self.right_menu is not None:
                pygame.draw.rect(screen, rgb.black, (self.right_menu_x, 0, 300, self.screen_y))
                pygame.draw.line(screen, rgb.white, (self.right_menu_x, 0), (self.right_menu_x, self.screen_y))
            
            if self.right_menu == 1:   # body list
                imgs = []
                names_screen = []
                for num, name in enumerate(self.names):
                    name = graphics.limit_text(name, self.fontbt, 280)   # limit names length to display on screen
                    if num == 0:
                        names_screen.append("Root: " + name)
                    else:
                        parent = self.names[self.ref[num]]
                        names_screen.append(name + "    @ " + parent)
                    imgs.append(self.body_imgs[int(self.types[num])])
                graphics.text_list_select(screen, names_screen, (self.r_menu_x_btn, 38), (280, 21), 26, self.selected, imgs)
            
            elif self.right_menu == 2 and self.selected is not None:   # data orbit
                texts = text_data_orb[:]
                for num, text in enumerate(text_data_orb):
                    if num == 0:
                        texts[0] = texts[0] + self.names[self.selected]
                    elif num == 1:
                        texts[1] = texts[1] + self.names[self.ref[self.selected]]
                    elif num == 8:
                        if self.orbit_data_menu[6] == -1:
                            texts[8] = texts[8] + "Clockwise"
                        else:
                            texts[8] = texts[8] + "Counter-clockwise"
                    elif num == 10:
                        texts[10] = texts[10] + str(datetime.timedelta(seconds=round(self.orbit_data_menu[8]/self.ptps)))
                    else:
                        texts[num] = texts[num] + metric.format_si(self.orbit_data_menu[num-2], 3)
                graphics.text_list(screen, texts, (self.r_menu_x_btn, 38), (280, 21), 26)
                
            elif self.right_menu == 3 and self.selected is not None:   # data body
                values_body = [self.names[self.selected],
                               body_types[int(self.types[self.selected])],
                               metric.format_si(self.mass[self.selected], 3),
                               metric.format_si(self.density[self.selected], 3),
                               metric.format_si(self.size[self.selected], 3),
                               metric.format_si(self.coi[self.selected], 3)]
                texts_body = []
                for i in range(len(text_data_body)):
                    texts_body.append(text_data_body[i] + values_body[i])
                texts_merged = texts_body[:]
                if int(self.types[self.selected]) in [0, 1, 2]:   # moon, planet, gas
                    color = self.color[self.selected]
                    values_planet = ["WIP",
                                     " R: " + str(color[0]) + "   G: " + str(color[1]) + "   B: " + str(color[2]),
                                     "WIP",
                                     "WIP",
                                     "WIP"]
                    texts_planet = []
                    for i in range(len(text_data_planet)):
                        if type(values_planet[i]) is str:
                            texts_planet.append(text_data_planet[i] + values_planet[i])
                        else:
                            texts_planet.append(values_planet[i])
                    texts_merged += texts_planet
                elif int(self.types[self.selected]) == 3:   # star
                    values_star = ["WIP",
                                   "WIP",
                                   "WIP",
                                   "WIP"]
                    texts_star = []
                    for i in range(len(text_data_star)):
                        texts_star.append(text_data_star[i] + values_star[i])
                    texts_merged += texts_star
                elif int(self.types[self.selected]) == 4:   # for bh
                    values_bh = [metric.format_si(self.rad_sc[self.selected], 3)]
                    texts_bh = []
                    for i in range(len(text_data_bh)):
                        texts_bh.append(text_data_bh[i] + values_bh[i])
                    texts_merged += texts_bh
                graphics.text_list(screen, texts_merged, (self.r_menu_x_btn, 38), (280, 21), 26)
            
            # top ui
            pygame.draw.rect(screen, rgb.black, (0, 0, self.screen_x, 22))
            pygame.draw.line(screen, rgb.white, (0, 22), (self.screen_x, 22), 1)
            graphics.text(screen, rgb.white, self.fontmd, str(datetime.timedelta(seconds=round(self.sim_time/self.ptps))), (2, 2))
            if self.pause:   # if paused
                graphics.text(screen, rgb.red1, self.fontmd, "PAUSED", (70, 2))
            else:
                graphics.text(screen, rgb.white, self.fontmd, "Warp: x" + str(int(self.warp)), (70, 2))
            if self.zoom < 10:   # rounding zoom to use max 4 chars (dot included)
                zoom_round = round(self.zoom, 2)
            elif self.zoom < 100:
                zoom_round = round(self.zoom, 1)
            elif self.zoom < 1000:
                zoom_round = int(self.zoom)
            else:
                zoom_round = "999+"
            graphics.text(screen, rgb.white, self.fontmd, "Zoom: x" + str(zoom_round), (160, 2))
            if self.move:
                # print position of view, here is not added zoom offset, this shows real position, y axis is inverted
                graphics.text(screen, rgb.white, self.fontmd,
                              "Pos: X:" + str(int(self.offset_x - self.screen_x / 2)) +
                              "; Y:" + str(-int(self.offset_y - self.screen_y / 2)),
                              (270, 2))
            
            # debug
            graphics.text(screen, rgb.gray1, self.fontmd, str(self.mouse_raw), (self.screen_x - 260, 2))
            graphics.text(screen, rgb.gray1, self.fontmd,
                          "[" + str(int(self.sim_coords(self.mouse_raw)[0])) + ", " +
                          str(int(self.sim_coords(self.mouse_raw)[1])) + "]",
                          (self.screen_x - 170, 2))
            graphics.text(screen, rgb.gray1, self.fontmd, "fps: " + str(int(clock.get_fps())), (self.screen_x - 50, 2))
    
    
    
    
    def main(self, screen, clock):
        run = True
        while run:
            for e in pygame.event.get():
                self.input_keys(e)
                self.input_mouse(e)
                self.ui_mouse(e)
                if self.state != 2:
                    state = self.state
                    self.state = 2
                    return state
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.physics(e)
                self.autosave(e)
            self.graphics(screen, clock)
            self.graphics_ui(screen, clock)
            pygame.display.flip()
            clock.tick(60)
        return self.state
