from ast import literal_eval as leval
import math
import os
import sys
import time
import copy
import pygame
import numpy as np

from volatilespace import fileops
from volatilespace import physics_editor
from volatilespace import physics_convert
from volatilespace.graphics import rgb
from volatilespace.graphics import graphics
from volatilespace.graphics import bg_stars
from volatilespace import textinput
from volatilespace import metric
from volatilespace import format_time
from volatilespace import defaults


physics = physics_editor.Physics()
graphics = graphics.Graphics()
bg_stars = bg_stars.Bg_Stars()
textinput = textinput.Textinput()


buttons_pause_menu = ["Resume",
                      "Save map",
                      "Load map",
                      "Settings",
                      "Quit without saving",
                      "Save and Quit"]
buttons_save = ["Cancel", "Save", "New save"]
buttons_load = ["Cancel", "Load"]
buttons_new_map = ["Cancel", "Create"]
body_types = ["Moon", "Solid planet", "Gas planet", "Star", "Black Hole"]
text_edit_orb = ["Selected body: ",
                 "Ref body: ",
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
text_edit_body = ["Body name: ", "Type: ", "Mass: ", "Density: ", "Radius: ", "COI altitude: "]
text_edit_planet = ["(Rotation period): ",
                    "Color: ",
                    "(Atmosphere amount): ",
                    "(Atmosphere height): ",
                    "(surface gravity): "]
text_edit_star = ["(Surface temp): ",
                  "(Luminosity): ",
                  "Color: ",
                  "(H/He ratio): "]
text_edit_bh = ["Schwarzschild radius: "]
text_edit_delete = "Delete body"
text_load_default = "Load default values"
prop_edit_orb = [0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0]
prop_edit_body = [1, 0, 1, 1, 0, 0]
prop_edit_planet = [1, 2, 1, 0, 0]
prop_edit_star = [0, 0, 0, 1]
prop_edit_bh = [0]
text_insert_body = ["Body name: ", "Type: ", "Mass: ", "Density: ", "Radius: "]
prop_insert_body = [1, 5, 1, 1, 0]
text_insert_start = "Start inserting"
text_insert_stop = "Stop inserting"
text_follow_mode = ["Disabled", "Active vessel", "Orbited body"]
text_grid_mode = ["Disabled", "Global", "Active vessel", "Orbited body"]


class Editor():
    def __init__(self):
        self.state = 2
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
        self.new_map = False
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
        self.btn_w_h_2 = (self.btn_w_l + 26)/2  # fits 2 btn in width of list button
        self.txt_y_margin = 8  # empty space between text and button edge
        self.btn_h = self.fontbt.get_height() + self.txt_y_margin * 2   # button height from font height
        self.btn_s = 36   # small square button
        self.btn_sm = 22   # very small square button
        self.space = 10   # space between buttons
        self.file_path = ""   # path to currently active file
        self.selected_path = ""   # path to selected file
        self.input_value = None   # which value is being text-inputed
        self.new_value_raw = ""   # when inputting new value
        self.edited_orbit = False   # if orbit is edited, on first click call kepler_inverse, but don't on next clicks
        self.gen_map_list()
        self.reload_settings()
        graphics.antial = self.antial
        
        # simulation related
        self.ptps = 59   # divisor to convert simulation time to real time (it is not 60 because userevent timer is rounded to 17ms)
        self.zoom = 0.15
        self.key_sens = 0.02   # sensitivity when pressing or holding wasd buttons
        self.select_sens = 5   # how many pixels are tolerable for mouse to move while selecting body
        self.drag_sens = 0.02   # drag sensitivity when inserting body
        self.warp_range = [1, 2, 3, 4, 5, 10, 50, 100]   # all possible warps, by order
        self.warp_index = 0
        self.warp = self.warp_range[self.warp_index]   # load current warp
        self.sim_time = 0
        self.pause = False
        self.enable_insert = False
        self.insert_body = False
        self.move = False
        self.selected = None 
        self.direction = None   # keyboard buttons wasd
        self.follow = False
        self.mouse = [0, 0]   # in simulation
        self.mouse_raw = [0, 0]   # on screen
        self.mouse_raw_old = [0, 0]
        self.zoom_x, self.zoom_y = 0, 0   # initial zoom offset
        self.offset_x = self.screen_x / 2   # initial centered offset to 0, 0 coordinates
        self.offset_y = self.screen_y / 2
        self.mouse_fix_x = False   # fix mouse movement when jumping off screen edge
        self.mouse_fix_y = False
        self.zoom_step = 0.05
        self.orbit_data = []   # additional data for right_menu
        self.sim_conf = {}   # simulation related config loaded from save file
        self.new_body_data = defaults.new_body_moon   # body related data when inserting new body
        self.precalc_data = physics.precalculate(self.new_body_data)   # body physics without adding it to sim
        self.vessel_data = None
        self.vessel_orb_data = None
        
        # ### DEBUG ###
        self.physics_debug_time = 1
        self.debug_timer = 0
        self.physics_debug_time_sum = 0
        self.physics_debug_percent = 0
        
        self.offset_old = np.array([self.offset_x, self.offset_y])
        self.grid_mode = 0   # grid mode: 0 - global, 1 - selected body, 2 - parent
        
        
        # icons
        menu_img = pygame.image.load("img/menu.png")
        body_list_img = pygame.image.load("img/body_list.png")
        insert_img = pygame.image.load("img/insert.png")
        orbit_img = pygame.image.load("img/orbit.png")
        body_img = pygame.image.load("img/body_edit.png")
        settings_img = pygame.image.load("img/settings.png")
        self.ui_imgs = [menu_img, body_list_img, insert_img, orbit_img, body_img, settings_img]
        follow_none_img = pygame.image.load("img/follow_none.png")
        follow_vessel_img = pygame.image.load("img/follow_vessel.png")
        follow_ref_img = pygame.image.load("img/follow_ref.png")
        self.top_ui_img_follow = [follow_none_img, follow_vessel_img, follow_ref_img]
        warp_0_img = pygame.image.load("img/warp_0.png")
        warp_0_img = graphics.fill(warp_0_img, rgb.red)
        warp_1_img = pygame.image.load("img/warp_1.png")
        warp_2_img = pygame.image.load("img/warp_2.png")
        warp_3_img = pygame.image.load("img/warp_3.png")
        self.top_ui_img_warp = [warp_0_img, warp_1_img, warp_2_img, warp_3_img]
        grid_global_img = pygame.image.load("img/grid_global.png")
        grid_vessel_img = pygame.image.load("img/grid_vessel.png")
        grid_ref_img = pygame.image.load("img/grid_ref.png")
        grid_disabled_img = graphics.fill(grid_global_img, rgb.gray0)
        self.top_ui_img_grid = [grid_disabled_img, grid_global_img, grid_vessel_img, grid_ref_img]
        self.top_ui_imgs = [warp_1_img, follow_vessel_img, grid_disabled_img]
        body_moon = pygame.image.load("img/moon.png")
        body_planet_solid = pygame.image.load("img/planet_solid.png")
        body_planet_gas = pygame.image.load("img/planet_gas.png")
        body_star = pygame.image.load("img/star.png")
        body_bh = pygame.image.load("img/bh.png")
        self.body_imgs = [body_moon, body_planet_solid, body_planet_gas, body_star, body_bh]
        
        bg_stars.set_screen()
        graphics.set_screen()
    
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.ask_x = self.screen_x/2 - (2*self.btn_w_h + self.space)/2
        self.ask_y = self.screen_y/2 + self.space
        self.pause_x = self.screen_x/2 - self.btn_w/2
        self.pause_y = self.screen_y/2 - (len(buttons_pause_menu) * self.btn_h + (len(buttons_pause_menu)-1) * self.space)/2
        self.pause_max_y = self.btn_h*len(buttons_pause_menu) + self.space*(len(buttons_pause_menu)+1)
        self.maps_x = self.screen_x/2 - self.btn_w_l/2
        self.maps_max_y = self.screen_y - 200
        self.list_limit = self.maps_max_y - self.btn_h - self.space
        self.maps_y = (self.screen_y - self.maps_max_y)/2
        self.maps_x_ui = self.maps_x - self.space
        self.maps_y_ui = self.maps_y + self.list_limit + self.space
        self.map_list_size = len(self.maps) * self.btn_h + len(self.maps) * self.space
        self.right_menu_x = self.screen_x - 300
        self.r_menu_limit = self.screen_y - 38 - self.space
        self.r_menu_x_btn = self.right_menu_x + self.space
    
    
    def reload_settings(self):
        """Reload all settings for editor and graphics, should be run every time editor is entered"""
        self.fullscreen = leval(fileops.load_settings("graphics", "fullscreen"))
        avail_res = pygame.display.list_modes()
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
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
        self.enable_insert = False
        self.insert_body = False
        self.autosave_event = pygame.USEREVENT + 1
        autosave_time = int(fileops.load_settings("game", "autosave_time")) * 60 * 1000   # min to ms
        pygame.time.set_timer(self.autosave_event, autosave_time)
    
    
    def gen_map_list(self):
        """Generate list of maps and select currently active file"""
        self.maps = fileops.gen_map_list()
        self.map_list_size = len(self.maps) * self.btn_h + len(self.maps) * self.space
        if len(self.maps) != 0:
            self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
        
        # limit text size
        for num, text in enumerate(self.maps[:, 1]):
            new_text = graphics.limit_text(text, self.fontbt, self.btn_w_l)
            if new_text != text:
                self.maps[num, 1] = new_text
        
        # find selected item based on currently active file
        selected_item = np.where(self.maps[:, 0] == self.file_path.strip("Maps/"))[0]
        if len(selected_item) == 0:
            self.selected_item = 0
        else:
            self.selected_item = selected_item[0]
            self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
    
    
    def load_system(self, system):
        """Load system from file and convert to newton orbit if needed"""
        game_data, self.sim_conf, body_data, body_orb_data, vessel_data, vessel_orb_data = fileops.load_file(system)
        self.sim_name = game_data["name"]
        self.sim_time = game_data["time"]
        self.names = body_data["name"]
        self.mass = body_data["mass"]
        self.density = body_data["den"]
        self.color = body_data["color"]
        self.vessel_data = None
        self.vessel_orb_data = None
        if body_orb_data["kepler"]:   # convert to newtonian model
            body_orb_data = physics_convert.to_newton(self.mass, body_orb_data, self.sim_conf["gc"], self.sim_conf["coi_coef"])
            self.vessel_data = vessel_data
            self.vessel_orb_data = vessel_orb_data
        physics.load_system(self.sim_conf, body_data, body_orb_data)   # add it to physics class
        self.file_path = system   # this path will be used for load/save
        self.disable_input = False
        self.disable_ui = False
        self.disable_labels = False
        self.gen_map_list()
        self.check_new_name()
        self.selected_item = 0
        self.selected = None
        self.do_pause(False)
        self.warp_index = 0
        self.warp = 1
        self.follow = 1
        self.grid_mode = 0
        self.focus_point([0, 0], 0.5)
        self.selected = 0
        self.top_ui_imgs = [self.top_ui_img_warp[1], self.top_ui_img_follow[1], self.top_ui_img_grid[0]]
        
        # userevent may not been run in first iteration, but this values are needed in graphics section:
        self.names, self.types, self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
    
    
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
        x_in_sim = coords_on_screen[0] / self.zoom - self.offset_x + self.zoom_x
        y_in_sim = -(coords_on_screen[1] - self.screen_y) / self.zoom - self.offset_y + self.zoom_y
        # y_on_screen = y_on_screen - screen_y   move origin from bottom-left to up-left. This is implemented in above line
        return [x_in_sim, y_in_sim]
    
    
    def load(self):
        """Loads system from "load" dialog."""
        if os.path.exists(self.selected_path):
            self.load_system(self.selected_path)
            self.names, self.types, self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
            self.file_path = self.selected_path   # change currently active file
            graphics.timed_text_init(rgb.gray0, self.fontmd, "Map loaded successfully", (self.screen_x/2, self.screen_y-70), 2, True)
        
        
    def save(self, path, name=None, silent=False):
        """Saves map to file. If name is None, name is not changed. 
        Automatically convert to kepler orbit if overwriting game"""
        base_color = physics.get_base_color()
        date = time.strftime("%d.%m.%Y %H:%M")
        body_orb_data = {"kepler": False, "pos": self.position, "vel": self.velocity}
        
        try:   # try to read file to check if it is game, if failed, do normal save
            _, _, _, orb_data_file, _, _ = fileops.load_file(path)
            kepler = orb_data_file["kepler"]
        except Exception:
            kepler = False
        
        if kepler:   # save with convert
            body_orb_data = physics_convert.to_kepler(self.mass, body_orb_data, self.sim_conf["gc"], self.sim_conf["coi_coef"])
            if not silent:
                graphics.timed_text_init(rgb.gray0, self.fontmd, "Map saved successfully to game file.", (self.screen_x/2, self.screen_y-70), 2, True)
        else:   # normal save
            if not silent:
                graphics.timed_text_init(rgb.gray0, self.fontmd, "Map saved successfully", (self.screen_x/2, self.screen_y-70), 2, True)
        
        body_data = {"name": self.names, "mass": self.mass, "den": self.density, "color": base_color}
        game_data = {"name": name, "date": date, "time": 0, "vessel": None}
        fileops.save_file(path, game_data, self.sim_conf,
                          body_data, body_orb_data,
                          self.vessel_data, self.vessel_orb_data)
    
    
    def quicksave(self):
        """Saves map to quicksave file."""
        self.save("Maps/quicksave.ini", "Quicksave - " + self.sim_name, True)
        graphics.timed_text_init(rgb.gray0, self.fontmd, "Quicksave...", (self.screen_x/2, self.screen_y-70), 2, True)
    
    
    def autosave(self, e):
        """Automatically saves current map to autosave.ini at predefined interval."""
        if e.type == self.autosave_event:
            self.save("Maps/autosave.ini", "Autosave - " + self.sim_name, True)
            graphics.timed_text_init(rgb.gray1, self.fontmd, "Autosave...", (self.screen_x/2, self.screen_y-70), 2, True)
    
    
    def do_pause(self, do=None):
        """Pause game, set warp to x1 and update top UI"""
        if do is not None:
            self.pause = do
        else:
            self.pause = not self.pause
        self.warp_index = 0
        self.warp = self.warp_range[self.warp_index]
        self.top_ui_imgs[0] = self.top_ui_img_warp[int(not self.pause)]
    
    
    def set_ui_warp(self):
        if self.warp_index < 3:
            ui_warp_index = 1
        elif self.warp_index < 5:
            ui_warp_index = 2
        else:
            ui_warp_index = 3
        self.top_ui_imgs[0] = self.top_ui_img_warp[ui_warp_index]
        graphics.timed_text_init(rgb.gray0, self.fontmd, "Time warp: x" + str(self.warp), (self.screen_x/2, self.screen_y-70), 1, True)
    
    
    def check_new_name(self):
        """Check if new body name is already taken and append number to it"""
        body_name = self.new_body_data["name"]
        if body_name in self.names:
            # check if number already exists and continue it
            last_space = body_name.rfind(" ")
            last_word = body_name[last_space+1:]
            try:
                num = int(last_word) + 1
            except Exception:
                body_name = self.new_body_data["name"] + " " + "1"
                last_space = body_name.rfind(" ")
                num = 2
            while body_name in self.names:
                body_name = self.new_body_data["name"][:last_space] + " " + str(num)
                num += 1
            self.new_body_data["name"] = body_name
    
    
    
    ###### --Keys-- ######
    def input_keys(self, e):
        """Simulation and menu keys"""
        if self.state != 2:   # when returning to editor menu
            self.state = 2 
        
        # new map menu
        if self.new_map:
            self.text = textinput.input(e)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.new_map = False
                    self.ask = None
                elif e.key == pygame.K_RETURN:
                    date = time.strftime("%d.%m.%Y %H:%M")
                    path = fileops.new_map(self.text, date)
                    self.save(path)
                    self.gen_map_list()
                    self.new_map = False
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
                        self.pause_menu = False
                        self.disable_input = False
                        self.ask = None
                    if self.menu == 0:
                        self.ask = "save"
                    elif self.menu == 1:
                        self.ask = "load"
                if not self.ask:
                    if e.key == pygame.K_DOWN:
                        if self.selected_item < len(self.maps)-1:
                            self.selected_item += 1
                            self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                    elif e.key == pygame.K_UP:
                        if self.selected_item > 0:
                            self.selected_item -= 1
                            self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
        
        # input in right ui
        elif self.input_value is not None:
            self.new_value_raw = textinput.input(e)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.input_value = None
                    self.check_new_name()
                elif e.key == pygame.K_RETURN:
                    if self.input_value == 0:
                        new_value = self.new_value_raw
                    else:
                        new_value = metric.parse_si(self.new_value_raw)
                    if new_value is not None:
                        if self.right_menu == 2:   # insert
                            if isinstance(self.input_value, int):
                                if self.input_value == 0:
                                    self.new_body_data["name"] = new_value
                                    self.check_new_name()   # check if name is already taken
                                if self.input_value == 2:
                                    self.new_body_data["mass"] = abs(new_value)
                                if self.input_value == 3:
                                    self.new_body_data["density"] = abs(new_value)
                            elif self.input_value is not None:   # if input value is string (for color)
                                color = self.new_body_data["color"]
                                if self.input_value[-1] == "a":   # R
                                    color[0] = int(new_value)
                                elif self.input_value[-1] == "b":   # G
                                    color[1] = int(new_value)
                                else:   # B
                                    color[2] = int(new_value)
                                color = np.clip(color, 0, 255)
                                self.new_body_data["color"] = color
                            self.precalc_data = physics.precalculate(self.new_body_data)
                            self.new_body_data["type"] = self.precalc_data["type"]
                        elif self.right_menu == 3:   # edit orbit
                            pe_d = self.orbit_data[0]
                            ap_d = None
                            ecc = self.orbit_data[2]
                            omega_deg = self.orbit_data[3]
                            mean_anomaly = self.orbit_data[4]
                            true_anomaly = None
                            direction = self.orbit_data[6]
                            if self.input_value == 2:   # pe
                                pe_d = abs(new_value)
                            if self.input_value == 3:   # ap
                                ap_d = abs(new_value)
                            if self.input_value == 4:   # ecc
                                ecc = abs(new_value)
                            if self.input_value == 5:   # pe_arg
                                omega_deg = new_value
                            if self.input_value == 6:   # Ma
                                mean_anomaly = new_value
                            if self.input_value == 7:   # Ta
                                true_anomaly = new_value
                            physics.kepler_inverse(self.selected, ecc, omega_deg, pe_d, mean_anomaly, true_anomaly, ap_d, direction)
                            self.edited_orbit = False
                        elif self.right_menu == 4:   # edit body
                            # replace original values
                            if isinstance(self.input_value, int):
                                if self.input_value == 0:   # body name
                                    if new_value != self.names[self.selected]:   # skip if name has not changed
                                        if new_value in self.names:   # if this name already exists
                                            graphics.timed_text_init(rgb.red, self.fontmd, "Body with this name already exists.", (self.screen_x/2, self.screen_y-70), 2, True)
                                        else:
                                            physics.set_body_name(self.selected, new_value)
                                elif self.input_value == 2:   # mass
                                    physics.set_body_mass(self.selected, abs(new_value))
                                elif self.input_value == 3:   # density
                                    physics.set_body_den(self.selected, abs(new_value))
                                elif int(self.types[self.selected]) in [0, 1, 2]:   # moon, planet, gas
                                    if self.input_value == 6:   # rotation period
                                        pass
                                elif int(self.types[self.selected]) == 3:   # star
                                    if self.input_value == 9:   # H/He ratio
                                        pass
                            elif self.input_value is not None:   # if input value is string (for color)
                                color = self.colors[self.selected]
                                if self.input_value[-1] == "a":   # R
                                    color[0] = int(new_value)
                                elif self.input_value[-1] == "b":   # G
                                    color[1] = int(new_value)
                                else:   # B
                                    color[2] = int(new_value)
                                color = np.clip(color, 0, 255)
                                physics.set_body_color(self.selected, color)
                        elif self.right_menu == 5:   # sim config
                            if self.input_value is not None:   # just in case
                                self.sim_conf[list(self.sim_conf.keys())[self.input_value]] = abs(new_value)
                                physics.load_conf(self.sim_conf)
                    else:
                        graphics.timed_text_init(rgb.red, self.fontmd, "Entered value is invalid", (self.screen_x/2, self.screen_y-70), 2, True)
                    self.input_value = None
        
        # in game
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.ask is None:
                    if self.pause_menu:
                        self.pause_menu = False
                        self.disable_input = False
                        self.do_pause(False)
                    else:
                        if self.enable_insert:
                            if self.insert_body:
                                self.insert_body = False
                            else:
                                self.enable_insert = False
                        else:
                            self.pause_menu = True
                            self.disable_input = True
                            self.do_pause(True)
                else:   # exit from ask window
                    self.ask = None
                    self.disable_input = False
            
            if not self.disable_input or self.allow_keys:
                if e.key == self.keys["interactive_pause"]:
                    self.do_pause()
                
                elif e.key == self.keys["focus_home"]:
                    self.follow = False
                    self.focus_point([0, 0], self.zoom)   # return to (0,0) coordinates
                    
                elif e.key == self.keys["cycle_follow_modes"]:
                    if self.selected is not None:
                        self.follow += 1   # cycle follow modes (0-disabled, 1-active vessel, 2-orbited body)
                        if self.follow > 2:
                            self.follow = 0
                        self.top_ui_imgs[1] = self.top_ui_img_follow[self.follow]
                        text = text_follow_mode[self.follow]
                        graphics.timed_text_init(rgb.gray0, self.fontmd, "Follow: " + text, (self.screen_x/2, self.screen_y-70), 1.5, True)
                
                elif e.key == self.keys["cycle_grid_modes"]:
                    self.grid_mode += 1   # cycle grid modes (0-global, 1-selected body, 2-parent)
                    if self.grid_mode > 3:
                        self.grid_mode = 0
                    self.top_ui_imgs[2] = self.top_ui_img_grid[self.grid_mode]
                    text = text_grid_mode[self.grid_mode]
                    graphics.timed_text_init(rgb.gray0, self.fontmd, "Grid: " + text, (self.screen_x/2, self.screen_y-70), 1.5, True)
                
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
                if not self.pause:
                    if e.key == self.keys["decrease_time_warp"]:
                        if self.warp_index != 0:   # stop index from going out of range
                            self.warp_index -= 1
                        self.warp = self.warp_range[self.warp_index]
                        self.set_ui_warp()
                    if e.key == self.keys["increase_time_warp"]:
                        if self.warp_index != len(self.warp_range)-1:   # stop index from going out of range
                            self.warp_index += 1
                        self.warp = self.warp_range[self.warp_index]
                        self.set_ui_warp()
                    if e.key == self.keys["stop_time_warp"]:
                        self.warp_index = 0
                        self.warp = self.warp_range[self.warp_index]
                        self.set_ui_warp()
                
                
                # changing velocity with wasd
                if self.selected is not None:
                    if e.key == self.keys["forward"]:
                        self.direction = "up"
                    if e.key == self.keys["backward"]:
                        self.direction = "down"
                    if e.key == self.keys["left"]:
                        self.direction = "left"
                    if e.key == self.keys["right"]:
                        self.direction = "right"
        
        if self.menu is None and self.selected is not None:
            if e.type == pygame.KEYDOWN:
                if e.key == self.keys["delete_body_in_editor"]:
                    state = physics.del_body(self.selected)
                    if state == 1:
                        graphics.timed_text_init(rgb.red, self.fontmd, "Cant delete body. There must be at least one body in simulation.", (self.screen_x/2, self.screen_y-70), 2, True)
                    else:
                        self.names, self.types, self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
                        self.selected = None
                        if self.right_menu in [3, 4]:
                            self.right_menu = None
                        
        
        if e.type == pygame.KEYUP and e.key in [self.keys["forward"], self.keys["backward"], self.keys["left"], self.keys["right"]]:
            self.direction = None   # when wasd key is released, clear direction to which velocity is added
        
        # add velocity to specific direction
        if self.direction is not None:
            _, _, _, _, _, _, velocity, _, _, _ = physics.get_bodies()   # get body velocity to be increased
            if self.direction == "up":   # new_velocity = old_velocity + key_sensitivity
                physics.set_body_vel(self.selected, [velocity[self.selected, 0], velocity[self.selected, 1] + self.key_sens])
            if self.direction == "down":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0], velocity[self.selected, 1] - self.key_sens])
            if self.direction == "left":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0] - self.key_sens, velocity[self.selected, 1]])
            if self.direction == "right":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0] + self.key_sens, velocity[self.selected, 1]])
    
    
    
    ###### --Simulation Mouse-- ######
    def input_mouse(self, e):
        """Input mouse for simulation"""
        self.mouse_raw = list(pygame.mouse.get_pos())
        self.mouse = list((self.mouse_raw[0]/self.zoom, -(self.mouse_raw[1] - self.screen_y)/self.zoom))   # mouse position on zoomed screen
        # y coordinate in self.mouse is negative for easier applying in formula to check if mouse is inside circle
        
        # disable input when mouse clicks on ui
        if not self.pause_menu and self.menu is None:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.mouse_raw[0] <= self.btn_s or self.mouse_raw[1] <= 22:
                    if self.disable_ui is False:
                        self.disable_input = True
                        self.allow_keys = True
                        self.enable_insert = False
                else:
                    self.disable_input = False
                    self.allow_keys = False
                if self.right_menu is not None:
                    if self.disable_ui is False:
                        if self.mouse_raw[0] >= self.right_menu_x:
                            self.disable_input = True
                            self.allow_keys = True
        
        if not self.disable_input:
            # inserting body
            if self.enable_insert:
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
                    self.insert_body = True 
                    self.new_position = self.sim_coords(self.mouse_raw)   # use variable, since reading from dict takes more time
                    self.new_body_data["position"] = self.new_position
                if e.type == pygame.MOUSEBUTTONUP and e.button == 1 and self.insert_body:
                    self.insert_body = False
                    drag_position = self.sim_coords(self.mouse_raw)
                    distance = math.dist(self.new_position, drag_position) * self.zoom
                    angle = math.atan2(drag_position[1] - self.new_position[1], drag_position[0] - self.new_position[0])
                    new_acc = distance * self.drag_sens   # decrease acceleration to reasonable value
                    new_acc_x = new_acc * math.cos(angle)   # separate acceleration components by axes
                    new_acc_y = new_acc * math.sin(angle)
                    self.new_body_data["velocity"] = [new_acc_x, new_acc_y]
                    self.check_new_name()
                    physics.add_body(self.new_body_data)
                
                if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:
                    if self.insert_body:
                        self.insert_body = False
                    elif self.enable_insert:
                        self.enable_insert = False
            
            # moving and selecting with lclick, or middle click in insert mode
            if e.type == pygame.MOUSEBUTTONDOWN:
                if (not self.enable_insert and e.button == 1) or (self.enable_insert and e.button == 2):
                    self.names, self.types, self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
                    self.move = True
                    self.mouse_old = self.mouse   # initial mouse position for movement
                    self.mouse_raw_old = self.mouse_raw
                    
            if e.type == pygame.MOUSEBUTTONUP:
                if (not self.enable_insert and e.button == 1) or (self.enable_insert and e.button == 2):
                    self.move = False
                    mouse_move = math.dist(self.mouse_raw, self.mouse_raw_old)
                    self.select_toggle = False
                    if e.button != 2:   # don't select body with middle click when in insert mode
                        if mouse_move < self.select_sens:
                            curves = physics.curve()
                            for body, body_pos in enumerate(self.position):
                                curve = np.column_stack(self.screen_coords(curves[:, body]))   # line coords on screen
                                diff = np.amax(curve, 0) - np.amin(curve, 0)
                                if body == 0 or diff[0]+diff[1] > 32:   # skip hidden bodies with too small orbits
                                    scr_radius = self.size[body]*self.zoom
                                    if scr_radius < 5:   # if body is small on screen, there is marker
                                        scr_radius = 8
                                    # if mouse is inside body radius on its location: (body_x - mouse_x)**2 + (body_y - mouse_y)**2 < radius**2
                                    if sum(np.square(self.screen_coords(body_pos) - self.mouse_raw)) < (scr_radius)**2:
                                        self.selected = body
                                        self.select_toggle = True   # do not exit select mode
                            if self.select_toggle is False and self.right_menu not in [3, 4]:   # if inside select mode and not in edit right menus
                                self.selected = None
                                if self.right_menu in [3, 4]:
                                    self.right_menu = None   # disable orbit and body edit
            
            
            # mouse wheel: change zoom
            if not self.disable_input:
                if e.type == pygame.MOUSEWHEEL:   # change zoom
                    if self.zoom > self.zoom_step or e.y == 1:   # prevent zooming below zoom_step, zoom can't be 0, but allow zoom to increase
                        self.zoom_step = self.zoom / 10
                        self.zoom += e.y * self.zoom_step
                        # zoom translation to center
                        self.zoom_x += (self.screen_x / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_x / (self.zoom * 2))
                        self.zoom_y += (self.screen_y / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_y / (self.zoom * 2))
                        # these values are added only to displayed objects, traces... But not to real position
    
    
    
    ###### --UI Mouse-- ######
    def ui_mouse(self, e):
        """Input mouse for menus"""
        btn_disable_input = False
        if self.disable_input and not self.allow_keys:
            btn_disable_input = True
        graphics.update_mouse(self.mouse_raw, self.click, btn_disable_input)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click = True
            
            # scroll bar
            if self.menu in [0, 1]:
                scrollable_len = max(0, self.map_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                if scrollable_len != 0:
                    scrollbar_pos = self.scroll * scrollbar_limit / scrollable_len
                else:
                    scrollbar_pos = 0
                scrollbar_x = self.maps_x + self.btn_w_l + self.space + 2
                scrollbar_y = self.maps_y - self.space + 3 + scrollbar_pos
                if scrollbar_x <= self.mouse_raw[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse_raw[1]-1 <= scrollbar_y + 40:
                    self.scrollbar_drag = True
                    self.scrollbar_drag_start = self.mouse[1]
                    self.ask = True   # dirty shortcut to disable safe buttons
        
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.click:
                
                # pause menu
                if self.pause_menu:
                    y_pos = self.pause_y
                    for num, _ in enumerate(buttons_pause_menu):
                        if self.pause_x <= self.mouse_raw[0]-1 <= self.pause_x + self.btn_w and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # resume
                                self.pause_menu = False
                                self.disable_input = False
                                self.do_pause(False)
                            elif num == 1:   # save
                                self.menu = 0
                                self.pause_menu = False
                                self.gen_map_list()
                            elif num == 2:   # load
                                self.menu = 1
                                self.pause_menu = False
                                self.gen_map_list()
                            elif num == 3:   # settings
                                self.state = 42   # go directly to main menu settings, but be able to return here
                            elif num == 4:   # quit
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.do_pause(False)
                            elif num == 5:   # save and quit
                                self.save(self.file_path, self.sim_name)
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.do_pause(False)
                        y_pos += self.btn_h + self.space
                
                # disable scrollbar_drag when release click
                elif self.scrollbar_drag:
                    self.scrollbar_drag = False
                    self.ask = None
                
                # save
                elif self.menu == 0:
                    # new map
                    if self.new_map:
                        x_pos = self.ask_x
                        for num in [0, 1]:
                            if x_pos <= self.mouse_raw[0]-1 <= x_pos+self.btn_w_h and self.ask_y+self.space <= self.mouse_raw[1]-1 <= self.ask_y+self.space+self.btn_h:
                                if num == 0:   # cancel
                                    pass
                                elif num == 1:
                                    path = fileops.new_map(self.text, time.strftime("%d.%m.%Y %H:%M"))
                                    self.save(path, name=self.text)
                                    self.gen_map_list()
                                self.new_map = False
                                self.ask = None
                            x_pos += self.btn_w_h + self.space
                    
                    else:   # disables bellow menus
                        # maps list
                        if self.maps_y - self.space <= self.mouse_raw[1]-1 <= self.maps_y + self.list_limit:
                            y_pos = self.maps_y - self.scroll
                            for num, _ in enumerate(self.maps[:, 1]):
                                if y_pos >= self.maps_y - self.btn_h - self.space and y_pos <= self.maps_y + self.list_limit:    # don't detect outside list area
                                    if self.maps_x <= self.mouse_raw[0]-1 <= self.maps_x + self.btn_w_l and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                                        self.selected_item = num
                                        self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                                        if self.first_click == num:   # detect double click
                                            if self.file_path == self.selected_path:   # don't ask to save over current file
                                                self.save(self.file_path)
                                                self.menu = None
                                                self.pause_menu = False
                                                self.disable_input = False
                                            else:
                                                self.ask = "save"
                                            self.click = False   # dont carry click to ask window
                                        self.first_click = num
                                y_pos += self.btn_h + self.space
                        
                        # ui
                        x_pos = self.maps_x_ui
                        for num, text in enumerate(buttons_save):
                            if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h_3 and self.maps_y_ui <= self.mouse_raw[1]-1 <= self.maps_y_ui + self.btn_h:
                                if num == 0:   # cancel
                                    self.menu = None
                                    self.pause_menu = True
                                elif num == 1:   # save
                                    if self.file_path == self.selected_path:   # don't ask to save over current file
                                        self.save(self.file_path)
                                        self.menu = None
                                        self.pause_menu = False
                                        self.disable_input = False
                                    else:
                                        self.ask = "save"
                                elif num == 2:   # new save
                                    self.new_map = True
                                    self.ask = True   # dirty shortcut to disable safe buttons
                            x_pos += self.btn_w_h_3 + self.space
                
                # load
                elif self.menu == 1:
                    # maps list
                    if self.maps_y - self.space <= self.mouse_raw[1]-1 <= self.maps_y + self.list_limit:
                        y_pos = self.maps_y - self.scroll
                        for num, text in enumerate(self.maps[:, 1]):
                            if y_pos >= self.maps_y - self.btn_h - self.space and y_pos <= self.maps_y + self.list_limit:    # don't detect outside list area
                                if self.maps_x <= self.mouse_raw[0]-1 <= self.maps_x + self.btn_w_l and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                                    self.selected_item = num
                                    self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                                    if self.first_click == num:   # detect double click
                                        self.ask = "load"
                                        self.click = False   # dont carry click to ask window
                                    self.first_click = num
                            y_pos += self.btn_h + self.space
                    
                    x_pos = self.maps_x_ui
                    for num, text in enumerate(buttons_load):
                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h_2 and self.maps_y_ui <= self.mouse_raw[1]-1 <= self.maps_y_ui + self.btn_h:
                            if num == 0:   # cancel
                                self.menu = None
                                self.pause_menu = True
                            elif num == 1:   # save
                                self.ask = "load"
                        x_pos += self.btn_w_h_2 + self.space
                
                # settings
                elif self.menu == 2:
                    pass
            
            # on click, disable text input:
            if self.click and not self.click_timer:
                if self.input_value == 0:
                    new_value = self.new_value_raw   # for names
                else:
                    new_value = metric.parse_si(self.new_value_raw)   # for values
                if new_value is not None:
                    if self.right_menu == 2:   # insert
                        if isinstance(self.input_value, int):
                            if self.input_value == 0:
                                self.new_body_data["name"] = new_value
                                self.check_new_name()
                            if self.input_value == 2:
                                self.new_body_data["mass"] = abs(new_value)
                            if self.input_value == 3:
                                self.new_body_data["density"] = abs(new_value)
                        elif self.input_value is not None:   # if input value is string (for color)
                            color = self.new_body_data["color"]
                            if self.input_value[-1] == "a":   # R
                                color[0] = int(new_value)
                            elif self.input_value[-1] == "b":   # G
                                color[1] = int(new_value)
                            else:   # B
                                color[2] = int(new_value)
                            color = np.clip(color, 0, 255)
                            self.new_body_data["color"] = color
                        self.precalc_data = physics.precalculate(self.new_body_data)
                        self.new_body_data["type"] = self.precalc_data["type"]
                    elif self.right_menu == 3:   # edit orbit
                        if self.edited_orbit:   # do this only at first click after changing orbit parameters
                            pe_d = self.orbit_data[0]
                            ap_d = None
                            ecc = self.orbit_data[2]
                            omega_deg = self.orbit_data[3]
                            mean_anomaly = self.orbit_data[4]
                            true_anomaly = None
                            direction = self.orbit_data[6]
                            if self.input_value == 2:   # pe
                                pe_d = abs(new_value)
                            if self.input_value == 3:   # ap
                                ap_d = abs(new_value)
                            if self.input_value == 4:   # ecc
                                ecc = abs(new_value)
                            if self.input_value == 5:   # pe_arg
                                omega_deg = new_value
                            if self.input_value == 6:   # Ma
                                mean_anomaly = new_value
                            if self.input_value == 7:   # Ta
                                true_anomaly = new_value
                            physics.kepler_inverse(self.selected, ecc, omega_deg, pe_d, mean_anomaly, true_anomaly, ap_d, direction)
                            self.edited_orbit = False
                    elif self.right_menu == 4:   # edit body
                        # replace original values
                        if isinstance(self.input_value, int):
                            if self.input_value == 0:   # body name
                                if new_value != self.names[self.selected]:
                                    if new_value in self.names:
                                        graphics.timed_text_init(rgb.red, self.fontmd, "Body with this name already exists.", (self.screen_x/2, self.screen_y-70), 2, True)
                                    else:
                                        physics.set_body_name(self.selected, new_value)
                            elif self.input_value == 2:   # mass
                                physics.set_body_mass(self.selected, abs(new_value))
                            elif self.input_value == 3:   # density
                                physics.set_body_den(self.selected, abs(new_value))
                            elif int(self.types[self.selected]) in [0, 1, 2]:   # moon, planet, gas
                                if self.input_value == 6:   # rotation period
                                    pass
                            elif int(self.types[self.selected]) == 3:   # star
                                if self.input_value == 9:   # H/He ratio
                                    pass
                        elif self.input_value is not None:   # if input value is string (for color)
                            color = self.colors[self.selected]
                            if self.input_value[-1] == "a":   # R
                                color[0] = int(new_value)
                            elif self.input_value[-1] == "b":   # G
                                color[1] = int(new_value)
                            else:   # B
                                color[2] = int(new_value)
                            color = np.clip(color, 0, 255)   # limit values to be 0 - 255
                            physics.set_body_color(self.selected, color)
                    elif self.right_menu == 5:   # sim config
                        if self.input_value is not None:   # just in case
                            self.sim_conf[list(self.sim_conf.keys())[self.input_value]] = abs(new_value)
                            physics.load_conf(self.sim_conf)
                    self.input_value = None
                else:
                    self.input_value = None
            
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
                            self.pause_menu = False
                            self.disable_input = False
                            self.ask = None
                        x_pos += self.btn_w_h + self.space
            
            if not self.disable_ui:
                # left ui
                if not self.input_value:   # don't change window if textinpt is active
                    y_pos = 23
                    for num, _ in enumerate(self.ui_imgs):
                        if 0 <= self.mouse_raw[0] <= 0 + self.btn_s and y_pos <= self.mouse_raw[1] <= y_pos + self.btn_s:
                            if num == 0:   # menu
                                self.pause_menu = True
                                self.disable_input = True
                                self.do_pause(True)
                                self.right_menu = None
                            else:
                                if self.right_menu == num:
                                    self.right_menu = None
                                else:
                                    if num in [3, 4]:
                                        if self.selected is not None:
                                            if num == 3 and self.selected == self.parents[self.selected]:   # don't display orbit edit for root body
                                                pass
                                            else:
                                                self.right_menu = num
                                                self.click = False
                                    else:
                                        self.right_menu = num
                        y_pos += self.btn_s + 1
                
                # top ui
                x_pos = 151
                for num, _ in enumerate(self.top_ui_imgs):
                    if x_pos <= self.mouse_raw[0] <= x_pos + self.btn_sm and 0 <= self.mouse_raw[1] <= self.btn_sm:
                        if num == 0:   # warp
                            self.warp_index += 1
                            if self.warp_index >= len(self.warp_range):
                                self.warp_index = 0
                            self.warp = self.warp_range[self.warp_index]
                            self.set_ui_warp()
                        if num == 1:
                            if self.selected is not None:   # follow
                                self.follow += 1   # cycle follow modes (0-disabled, 1-active vessel, 2-orbited body)
                                if self.follow > 2:
                                    self.follow = 0
                                self.top_ui_imgs[1] = self.top_ui_img_follow[self.follow]
                                text = text_follow_mode[self.follow]
                                graphics.timed_text_init(rgb.gray0, self.fontmd, "Follow mode: " + text, (self.screen_x/2, self.screen_y-70), 1.5, True)
                        if num == 2:
                            self.grid_mode += 1   # grid
                            if self.grid_mode > 3:
                                self.grid_mode = 0
                            self.top_ui_imgs[2] = self.top_ui_img_grid[self.grid_mode]
                            text = text_grid_mode[self.grid_mode]
                            graphics.timed_text_init(rgb.gray0, self.fontmd, "Grid mode: " + text, (self.screen_x/2, self.screen_y-70), 1.5, True)
                    x_pos += self.btn_sm + 1
                
                # right ui
                if not self.click_timer:
                    if self.right_menu == 1:   # body list
                        y_pos = 38
                        for num, _ in enumerate(self.names):
                            if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                self.selected = num
                                self.follow = True
                            y_pos += 26
                    if self.right_menu == 2:   # insert
                        y_pos = 38
                        prop_merged = prop_insert_body.copy()
                        text_merged = text_insert_body.copy()
                        new_body_type = self.new_body_data["type"]
                        if new_body_type in [0, 1, 2]:   # moon, planet, gas
                            prop_merged = prop_insert_body + prop_edit_planet
                            text_merged = text_insert_body + text_edit_planet
                        elif new_body_type == 3:   # star
                            prop_merged = prop_insert_body + prop_edit_star
                            text_merged = text_insert_body + text_edit_star
                        elif new_body_type == 4:   # bh
                            prop_merged.append(0)
                        break_flag = False
                        prop_merged.append(3)
                        for num, editable in enumerate(prop_merged):
                            if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                if num == 1:   # select body type
                                    x_pos = self.r_menu_x_btn
                                    w_short = (280 + 10) / len(body_types) - 10
                                    for num, _ in enumerate(body_types):
                                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + w_short:
                                            if num == 0:
                                                self.new_body_data = copy.deepcopy(defaults.new_body_moon)
                                            elif num == 1:
                                                self.new_body_data = copy.deepcopy(defaults.new_body_planet)
                                            elif num == 2:
                                                self.new_body_data = copy.deepcopy(defaults.new_body_gas)
                                            elif num == 3:
                                                self.new_body_data = copy.deepcopy(defaults.new_body_star)
                                            elif num == 4:
                                                self.new_body_data = copy.deepcopy(defaults.new_body_bh)
                                            self.check_new_name()
                                            self.precalc_data = physics.precalculate(self.new_body_data)
                                            self.input_value = None
                                            break
                                        x_pos += w_short + 10
                                elif editable in [1, 2]:
                                    init_values = [self.new_body_data["name"],
                                                   None,
                                                   metric.format_si(self.new_body_data["mass"], 3),
                                                   metric.format_si(self.new_body_data["density"], 3),
                                                   None]
                                    if num >= len(prop_insert_body):
                                        if new_body_type in [0, 1, 2]:   # moon, planet, gas
                                            init_values += ["WIP", "WIP", "WIP", "WIP", "WIP"]
                                            if num == 6:   # color
                                                x_pos = self.r_menu_x_btn + 58
                                                for num in range(3):
                                                    if x_pos <= self.mouse_raw[0]-1 <= x_pos + 53:
                                                        if num == 0:
                                                            self.input_value = "6a"
                                                            fixed_init_text = "R: "
                                                            color_componet = self.new_body_data["color"][0]
                                                        elif num == 1:
                                                            self.input_value = "6b"
                                                            fixed_init_text = "G: "
                                                            color_componet = self.new_body_data["color"][1]
                                                        elif num == 2:
                                                            self.input_value = "6c"
                                                            fixed_init_text = "B: "
                                                            color_componet = self.new_body_data["color"][2]
                                                        textinput.initial_text(str(color_componet), fixed_init_text, x_corr=-3, limit_len=3)
                                                        self.click = False
                                                        self.first_click = True   # activate timer for double click
                                                        break_flag = True   # don't run code after this
                                                        break
                                                    x_pos += 59
                                        if break_flag:
                                            break
                                        elif new_body_type == 3:   # star
                                            init_values += ["WIP", "WIP", "WIP", "WIP"]
                                    self.input_value = num
                                    textinput.initial_text(init_values[num], text_merged[num])
                                    self.click = False
                                    self.first_click = True   # activate timer for double click
                            if editable in [3, 4]:
                                y_pos += 12
                                if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                    self.enable_insert = not self.enable_insert
                            y_pos += 26
                    if self.right_menu == 3:   # edit orbit
                        y_pos = 38
                        for num, editable in enumerate(prop_edit_orb):
                            if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                if editable == 1:
                                    self.input_value = num
                                    if num < 2:
                                        if num == 0:
                                            init_value = self.names[self.selected]
                                    elif num == 8:   # change orbit direction button
                                        pe_d = self.orbit_data[0]
                                        ap_d = None
                                        ecc = self.orbit_data[2]
                                        omega_deg = self.orbit_data[3]
                                        mean_anomaly = -self.orbit_data[4]   # inverted
                                        true_anomaly = None
                                        direction = self.orbit_data[6]
                                        direction = -direction
                                        self.input_value = None
                                        physics.kepler_inverse(self.selected, ecc, omega_deg, pe_d, mean_anomaly, true_anomaly, ap_d, direction)
                                        self.edited_orbit = False
                                        break
                                    else:
                                        init_value = metric.format_si(self.orbit_data[num - 2], 3)
                                    self.edited_orbit = True   # on first click or enter call kepler_inverse, but don't on next clicks
                                    textinput.initial_text(init_value, text_edit_orb[num])
                                    self.click = False
                                    self.first_click = True
                            y_pos += 26
                    if self.right_menu == 4:   # edit body
                        y_pos = 38
                        prop_merged = prop_edit_body.copy()
                        text_merged = text_edit_body.copy()
                        if int(self.types[self.selected]) in [0, 1, 2]:   # moon, planet, gas
                            prop_merged = prop_edit_body + prop_edit_planet
                            text_merged = text_edit_body + text_edit_planet
                        elif int(self.types[self.selected]) == 3:   # star
                            prop_merged = prop_edit_body + prop_edit_star
                            text_merged = text_edit_body + text_edit_star
                        break_flag = False
                        prop_merged.append(3)
                        for num, editable in enumerate(prop_merged):
                            if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                if editable in [1, 2]:
                                    init_values = [self.names[self.selected],
                                                   None,
                                                   metric.format_si(self.mass[self.selected], 3),
                                                   metric.format_si(self.density[self.selected], 3),
                                                   metric.format_si(self.size[self.selected], 3),
                                                   metric.format_si(self.coi[self.selected], 3)]
                                    if num >= len(prop_edit_body):
                                        if int(self.types[self.selected]) in [0, 1, 2]:   # moon, planet, gas
                                            init_values += ["WIP", "WIP", "WIP", "WIP", "WIP"]
                                            if num == 7:   # color
                                                x_pos = self.r_menu_x_btn + 58
                                                for num in range(3):
                                                    if x_pos <= self.mouse_raw[0]-1 <= x_pos + 53:
                                                        if num == 0:
                                                            self.input_value = "7a"
                                                            fixed_init_text = "R: "
                                                            color_componet = self.colors[self.selected, 0]
                                                        elif num == 1:
                                                            self.input_value = "7b"
                                                            fixed_init_text = "G: "
                                                            color_componet = self.colors[self.selected, 1]
                                                        elif num == 2:
                                                            self.input_value = "7c"
                                                            fixed_init_text = "B: "
                                                            color_componet = self.colors[self.selected, 2]
                                                        textinput.initial_text(str(color_componet), fixed_init_text, x_corr=-3, limit_len=3)
                                                        self.click = False
                                                        self.first_click = True
                                                        break_flag = True   # don't run code after this
                                                        break
                                                    x_pos += 59
                                        if break_flag:
                                            break
                                        elif int(self.types[self.selected]) == 3:   # star
                                            init_values += ["WIP", "WIP", "WIP", "WIP"]
                                    self.input_value = num
                                    textinput.initial_text(init_values[num], text_merged[num])
                                    self.click = False
                                    self.first_click = True
                            if editable == 3:
                                y_pos += 12
                                if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 19:
                                    state = physics.del_body(self.selected)
                                    if state == 1:
                                        graphics.timed_text_init(rgb.red, self.fontmd, "Cant delete body. There must be at least one body in simulation.", (self.screen_x/2, self.screen_y-70), 2, True)
                                    else:
                                        self.names, self.types, self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
                                        self.selected = None
                                        self.right_menu = None
                            y_pos += 26
                    if self.right_menu == 5:   # sim config
                        y_pos = 38
                        for num, item in enumerate(self.sim_conf.items()):
                            if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                self.input_value = num
                                textinput.initial_text(str(item[1]), item[0] + ": ")
                                self.click = False
                                self.first_click = True
                            y_pos += 26
                        y_pos += 12
                        if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                            self.sim_conf = defaults.sim_config.copy()
                            physics.load_conf(self.sim_conf)
                
                
            
            # scrollbar
            if e.type == pygame.MOUSEWHEEL and (self.menu == 0 or self.menu == 1):
                if self.scrollbar_drag is False:
                    # scrolling inside list area
                    if self.maps_x-self.space <= self.mouse_raw[0]-1 <= self.maps_x+self.btn_w_l+self.space+16 and self.maps_y-self.space <= self.mouse_raw[1]-1 <= self.maps_y+self.list_limit:
                        self.scroll -= e.y * self.scroll_sens
                        if self.scroll < 0:
                            self.scroll = 0
                        elif self.scroll > max(0, self.map_list_size - self.list_limit):
                            self.scroll = max(0, self.map_list_size - self.list_limit)
            
            self.click = False
        
        # moving scrollbar with cursor
        if self.scrollbar_drag:
            if self.menu == 0 or self.menu == 1:
                scrollbar_pos = self.mouse_raw[1] - self.maps_y
                scrollable_len = max(0, self.map_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                self.scroll = scrollable_len * scrollbar_pos / scrollbar_limit
                if self.scroll < 0:
                    self.scroll = 0
                elif self.scroll > max(0, self.map_list_size - self.list_limit):
                    self.scroll = max(0, self.map_list_size - self.list_limit)
        
        return self.state
    
    
    
    ###### --Physics-- ######
    def physics(self, e):
        """Do simulation physics with warp and pause"""
        body_del = None
        debug_time = time.time()   # ### DEBUG ###
        if e.type == pygame.USEREVENT:
            if self.pause is False:
                for _ in range(self.warp):
                    physics.gravity()
                    physics.body()
                    body_del = physics.inelastic_collision()
                    self.sim_time += 1
        
        if self.pause is False:
            if body_del is not None:   # if there is collision
                if self.selected is not None:
                    if body_del == self.selected:   # if selected body is deleted:
                        self.selected = None
                    elif body_del < self.selected:   # if body before selected one is deleted
                        self.selected -= 1
                    self.direction = None
            self.names, self.types, self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
            physics.kepler_basic()
            self.semi_major, self.semi_minor, self.coi, self.parents = physics.get_body_orbits()
            self.colors = physics.body_color()
            physics.classify()
            
            self.physics_debug_time = time.time() - debug_time   # ### DEBUG ###
    
    
    
    ###### --Graphics-- ######
    def graphics(self, screen):
        """Drawing simulation stuff on screen"""
        screen.fill((0, 0, 0))
        
        
        # follow body (this must be before drawing objects to prevent them from vibrating when moving)
        if self.follow and self.selected is not None:
            if self.selected is not None:
                if self.follow == 1:
                    self.offset_x = - self.position[self.selected, 0] + self.screen_x / 2
                    self.offset_y = - self.position[self.selected, 1] + self.screen_y / 2
                else:
                    ref = self.parents[self.selected]
                    self.offset_x = - self.position[ref, 0] + self.screen_x / 2
                    self.offset_y = - self.position[ref, 1] + self.screen_y / 2
            else:
                self.follow = 0
        
        # screen movement
        if self.move:   # this is not in userevent to allow moving while paused
            if self.mouse_fix_x:   # when mouse jumps from one edge to other:
                self.mouse_old[0] = self.mouse[0]   # don't calculate that as mouse movement
                self.mouse_fix_x = False
            if self.mouse_fix_y:
                self.mouse_old[1] = self.mouse[1]
                self.mouse_fix_y = False
            
            mouse_move = math.dist((self.mouse_raw[0], self.mouse_raw[1]), (self.mouse_raw_old[0], self.mouse_raw_old[1]))
            self.offset_x += self.mouse[0] - self.mouse_old[0]   # add mouse movement to offset
            self.offset_y += self.mouse[1] - self.mouse_old[1]
            
            if mouse_move > self.select_sens:   # stop following if mouse distance is more than sensitivity
                self.follow = False
            
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
            speed = math.sqrt(offset_diff.dot(offset_diff))/3   # speed as movement vector magnitude
            while speed > 300:   # limits speed when view is jumping (focus home, distant body...)
                speed = math.sqrt(speed)
            direction = math.atan2(offset_diff[1], offset_diff[0])   # movement vector angle from atan2
            bg_stars.draw_bg(screen, speed, direction, self.zoom)
        
        
        # background lines grid
        if self.grid_mode:
            if self.grid_mode == 1:   # grid mode: home
                origin = self.screen_coords([0, 0])
            if self.selected is not None:
                if self.grid_mode == 2:      # grid mode: selected body
                    if self.follow is False:
                        origin = self.screen_coords(self.position[self.selected])
                    else:   # When following body, origin is in center of screen
                        origin = [(- self.zoom_x + self.screen_x/2) * self.zoom, self.screen_y - (- self.zoom_y + self.screen_y/2) * self.zoom]
                if self.grid_mode == 3:   # grid mode: parent of selected body
                    origin = self.screen_coords(self.position[self.parents[self.selected]])
            else:
                origin = self.screen_coords([0, 0])
            graphics.draw_grid(screen, self.grid_mode, origin, self.zoom)
        
        
        # bodies drawing
        curves = physics.curve()
        for body in range(len(self.mass)):
            curve = np.column_stack(self.screen_coords(curves[:, body]))   # line coords on screen
            diff = np.amax(curve, 0) - np.amin(curve, 0)
            if body == 0 or diff[0]+diff[1] > 32:   # skip bodies with too small orbits
                
                # draw orbit curve lines
                if body != 0:   # skip root
                    line_color = np.where(self.colors[body] > 255, 255, self.colors[body])
                    graphics.draw_lines(screen, tuple(line_color), curve, 2)
                
                # draw bodies
                scr_body_size = self.size[body] * self.zoom
                body_color = tuple(self.colors[body])
                if scr_body_size >= 5:
                    graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.position[body]), scr_body_size)
                else:   # if body is too small, draw marker with fixed size
                    graphics.draw_circle_fill(screen, rgb.gray1, self.screen_coords(self.position[body]), 6)
                    graphics.draw_circle_fill(screen, rgb.gray2, self.screen_coords(self.position[body]), 5)
                    graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.position[body]), 4)
                
                # select body
                if self.selected is not None and self.selected == body:
                    parent = self.parents[body]
                    body_pos = self.position[body, :]
                    ecc, periapsis, pe_d, pe_t, apoapsis, ap_d, ap_t, pe_arg, ma, ta, direction, distance, period, speed_orb, speed_hor, speed_vert = physics.kepler_advanced(body)   # get advanced kepler parameters for selected body
                    if self.right_menu == 3:
                        self.orbit_data = [pe_d, ap_d, ecc, pe_arg, ma, ta, direction, distance, period, speed_orb, speed_hor, speed_vert]
                    
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
                            parent_scr = self.screen_coords(self.position[parent])
                            if self.size[parent] * self.zoom >= 5:
                                graphics.draw_circle(screen, rgb.red1, parent_scr, self.size[parent] * self.zoom + 4, 1)   # parent circle
                            else:
                                graphics.draw_circle(screen, rgb.red1, parent_scr, 8, 1)   # for body marker
                            if parent != 0:
                                if self.coi[parent] * self.zoom >= 8:
                                    graphics.draw_circle(screen, rgb.red1, parent_scr, self.coi[parent] * self.zoom, 1)   # parent circle of influence
                            
                            # ap and pe
                            if ap_d > 0:
                                ap_scr = self.screen_coords(apoapsis)
                            else:   # in case of hyperbola/parabola (ap_d is negative)
                                ap_scr = self.screen_coords(periapsis)
                            ap_scr_dist = abs(parent_scr - ap_scr)
                            if ap_scr_dist[0] > 8 or ap_scr_dist[1] > 8:   # dont draw Ap and Pe if Ap is too close to parent
                                
                                pe_scr = self.screen_coords(periapsis)
                                pe_scr_dist = abs(parent_scr - pe_scr)
                                if pe_scr_dist[0] > 8 or pe_scr_dist[1] > 8:   # dont draw Pe if it is too close to parent
                                    # periapsis location marker, text: distance and time to it
                                    graphics.draw_circle_fill(screen, rgb.lime1, pe_scr, 3)   # periapsis marker
                                    graphics.text(screen, rgb.lime1, self.fontsm, "Periapsis: " + str(round(pe_d, 1)), (pe_scr[0], pe_scr[1] + 7), True)
                                    graphics.text(screen, rgb.lime1, self.fontsm,
                                                  "T - " + format_time.to_date(int(pe_t/self.ptps)),
                                                  (pe_scr[0], pe_scr[1] + 17), True)
                                
                                if ecc < 1:   # if orbit is ellipse
                                    # apoapsis location marker, text: distance and time to it
                                    graphics.draw_circle_fill(screen, rgb.lime1, ap_scr, 3)   # apoapsis marker
                                    graphics.text(screen, rgb.lime1, self.fontsm, "Apoapsis: " + str(round(ap_d, 1)), (ap_scr[0], ap_scr[1] + 7), True)
                                    graphics.text(screen, rgb.lime1, self.fontsm,
                                                  "T - " + format_time.to_date(int(ap_t/self.ptps)),
                                                  (ap_scr[0], ap_scr[1] + 17), True)
        
        # inserting new body
        if self.enable_insert is True:
            if not self.insert_body:
                graphics.draw_circle_fill(screen, self.precalc_data["real_color"], self.mouse_raw, self.precalc_data["radius"] * self.zoom)
            else:
                # draw new body before released
                graphics.draw_circle_fill(screen, self.precalc_data["real_color"], self.screen_coords(self.new_position), self.precalc_data["radius"] * self.zoom)
                # draw line connecting body and release point
                if not self.disable_labels:
                    graphics.draw_line(screen, rgb.red, self.screen_coords(self.new_position), (self.mouse_raw[0], self.mouse_raw[1]), 1)
                # draw predicted orbit line
                drag_position = self.sim_coords(self.mouse_raw)
                distance = math.dist(self.new_position, drag_position) * self.zoom
                angle = math.atan2(drag_position[1] - self.new_position[1], drag_position[0] - self.new_position[0])
                new_acc = distance * self.drag_sens
                new_acc_x = new_acc * math.cos(angle)
                new_acc_y = new_acc * math.sin(angle)
                new_body_velocity = [new_acc_x, new_acc_y]
                curve = physics.precalc_curve(self.new_body_data["position"], new_body_velocity)
                curve = np.column_stack(self.screen_coords(curve))
                graphics.draw_lines(screen, rgb.gray2, curve, 2)
        
    
    
    
    ###### --Menus-- ######
    def graphics_ui(self, screen, clock):
        """Drawing GUI menus"""
        
        # pause menu
        if self.pause_menu:
            border_rect = [self.pause_x-self.space, self.pause_y-self.space, self.btn_w+2*self.space, self.pause_max_y]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
            graphics.buttons_vertical(screen, buttons_pause_menu, (self.pause_x, self.pause_y), safe=True)
        
        # save menu
        if self.menu == 0:
            border_rect = [self.maps_x-2*self.space, self.maps_y-2*self.space, self.btn_w_l+4*self.space + 16, self.maps_max_y+3*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            graphics.buttons_list(screen, self.maps[:, 1], (self.maps_x, self.maps_y), self.list_limit, self.scroll, self.selected_item, safe=not bool(self.ask))
            graphics.buttons_horizontal(screen, buttons_save, (self.maps_x_ui, self.maps_y_ui), alt_width=self.btn_w_h_3, safe=not bool(self.ask))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
        
        # load menu
        elif self.menu == 1:
            border_rect = [self.maps_x-2*self.space, self.maps_y-2*self.space, self.btn_w_l+4*self.space + 16, self.maps_max_y+3*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            graphics.buttons_list(screen, self.maps[:, 1], (self.maps_x, self.maps_y), self.list_limit, self.scroll, self.selected_item, safe=not bool(self.ask))
            graphics.buttons_horizontal(screen, buttons_load, (self.maps_x - self.space, self.maps_y_ui), alt_width=self.btn_w_h_2, safe=not bool(self.ask))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
        
        # asking to load/save
        if self.ask == "load":
            ask_txt = "Loading will overwrite unsaved changes."
            graphics.ask(screen, ask_txt, self.maps[self.selected_item, 1], "Load", (self.ask_x, self.ask_y))
        elif self.ask == "save":
            ask_txt = "Are you sure you want to overwrite this save:"
            graphics.ask(screen, ask_txt, self.maps[self.selected_item, 1], "Save", (self.ask_x, self.ask_y))
        
        # screenshot
        if self.screenshot:
            date = time.strftime("%Y-%m-%d %H-%M-%S")
            screenshot_path = "Screenshots/Screenshot from " + date + ".png"
            pygame.image.save(screen, screenshot_path)
            if not self.disable_ui:
                graphics.timed_text_init(rgb.gray0, self.fontmd, "Screenshot saved at: " + screenshot_path, (self.screen_x/2, self.screen_y-70), 2, True)
            self.screenshot = False
        
        # new map
        if self.new_map:
            border_rect = [self.ask_x-self.space, self.ask_y-40-self.btn_h, self.btn_w_h*2+3*self.space, self.btn_h+40+self.btn_h+2*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
            graphics.text(screen, rgb.white, self.fontbt, "New Map", (self.screen_x/2,  self.ask_y-20-self.btn_h), True)
            textinput.graphics(screen, clock, self.fontbt, (self.ask_x, self.ask_y-self.btn_h), (self.btn_w_h*2+self.space, self.btn_h))
            graphics.buttons_horizontal(screen, buttons_new_map, (self.ask_x, self.ask_y+self.space), safe=True)
    
        # double click counter   # not graphics related, but must be outside of input functions
        if self.first_click is not None:
            self.click_timer += clock.get_fps() / 60
            if self.click_timer >= 0.4 * 60:
                self.first_click = None
                self.click_timer = 0
        
        
        if not self.disable_ui:
            graphics.timed_text(screen, clock)
            
            # left ui
            pygame.draw.rect(screen, rgb.black, (0, 0, self.btn_s, self.screen_y))
            if self.selected is not None:
                prop_l = None
                if self.selected == self.parents[self.selected]:
                    prop_l = [None, None, None, 0, None, None]
            else:
                prop_l = [None, None, None, 0, 0, None]
            graphics.buttons_small_v(screen, self.ui_imgs, (0, 23), prop=prop_l, selected=self.right_menu)
            pygame.draw.line(screen, rgb.white, (self.btn_s, 0), (self.btn_s, self.screen_y), 1)
            
            # right ui
            if self.right_menu is not None:
                pygame.draw.rect(screen, rgb.black, (self.right_menu_x, 0, 300, self.screen_y))
                pygame.draw.line(screen, rgb.white, (self.right_menu_x, 0), (self.right_menu_x, self.screen_y))
            
            if self.right_menu == 1:   # body list
                imgs = []
                names_screen = []
                for num, name in enumerate(self.names):
                    name = graphics.limit_text(name, self.fontbt, 280)   # limit names length
                    if num == 0:
                        names_screen.append("Root: " + name)
                    else:
                        parent = self.names[self.parents[num]]
                        names_screen.append(name + "    @ " + parent)
                    imgs.append(self.body_imgs[int(self.types[num])])
                graphics.text_list_select(screen, names_screen, (self.r_menu_x_btn, 38), (280, 21), 26, self.selected, imgs)
            
            elif self.right_menu == 2:   # insert
                values_body = [self.new_body_data["name"],
                               "",
                               metric.format_si(self.new_body_data["mass"], 3),
                               metric.format_si(self.new_body_data["density"], 3),
                               metric.format_si(self.precalc_data["radius"], 3),]
                texts_body = []
                for i, _ in enumerate(text_insert_body):
                    texts_body.append(text_insert_body[i] + values_body[i])
                prop_merged = prop_insert_body
                texts_merged = texts_body[:]
                new_body_type = self.new_body_data["type"]
                if new_body_type in [0, 1, 2]:   # moon, planet, gas
                    prop_merged = prop_insert_body + prop_edit_planet
                    values_planet = ["WIP",
                                     self.new_body_data["color"],
                                     "WIP",
                                     "WIP",
                                     "WIP"]
                    texts_planet = []
                    for i, _ in enumerate(text_insert_body):
                        if isinstance(values_planet[i], (int, str)):
                            texts_planet.append(text_insert_body[i] + values_planet[i])
                        else:
                            texts_planet.append(values_planet[i])
                    texts_merged += texts_planet
                elif new_body_type == 3:   # star
                    prop_merged = prop_insert_body + prop_edit_star
                    values_star = ["WIP",
                                   "WIP",
                                   "WIP",
                                   "WIP"]
                    texts_star = []
                    for i, _ in enumerate(text_edit_star):
                        texts_star.append(text_edit_star[i] + values_star[i])
                    texts_merged += texts_star
                elif new_body_type == 4:   # for bh
                    prop_merged = prop_insert_body + prop_edit_bh
                    values_bh = [metric.format_si(self.precalc_data["rad_sc"], 3)]
                    texts_bh = []
                    for i, _ in enumerate(text_edit_bh):
                        texts_bh.append(text_edit_bh[i] + values_bh[i])
                    texts_merged += texts_bh
                if self.enable_insert:
                    texts_merged.append(text_insert_stop)
                    prop_merged.append(3)
                else:
                    texts_merged.append(text_insert_start)
                    prop_merged.append(4)
                graphics.text_list(screen, texts_merged, (self.r_menu_x_btn, 38), (280, 21), 26, imgs=self.body_imgs, prop=prop_merged, selected=new_body_type)
            
            elif self.right_menu == 3 and self.selected is not None:   # edit orbit
                texts = text_edit_orb[:]
                for num, text in enumerate(text_edit_orb):
                    if num == 0:
                        texts[0] = texts[0] + self.names[self.selected]
                    elif num == 1:
                        texts[1] = texts[1] + self.names[self.parents[self.selected]]
                    elif num == 8:
                        if self.orbit_data[6] == -1:
                            texts[8] = texts[8] + "Clockwise"
                        else:
                            texts[8] = texts[8] + "Counter-clockwise"
                    elif num == 10:
                        texts[10] = texts[10] + format_time.to_date(int(self.orbit_data[8]/self.ptps))
                    else:
                        texts[num] = texts[num] + metric.format_si(self.orbit_data[num-2], 3)
                graphics.text_list(screen, texts, (self.r_menu_x_btn, 38), (280, 21), 26, prop=prop_edit_orb)
                
            elif self.right_menu == 4 and self.selected is not None:   # edit body
                values_body = [self.names[self.selected],
                               body_types[int(self.types[self.selected])],
                               metric.format_si(self.mass[self.selected], 3),
                               metric.format_si(self.density[self.selected], 3),
                               metric.format_si(self.size[self.selected], 3),
                               metric.format_si(self.coi[self.selected], 3)]
                texts_body = []
                for i, _ in enumerate(text_edit_body):
                    texts_body.append(text_edit_body[i] + values_body[i])
                prop_merged = prop_edit_body
                texts_merged = texts_body[:]
                if int(self.types[self.selected]) in [0, 1, 2]:   # moon, planet, gas
                    prop_merged = prop_edit_body + prop_edit_planet
                    values_planet = ["WIP",
                                     self.colors[self.selected],
                                     "WIP",
                                     "WIP",
                                     "WIP"]
                    texts_planet = []
                    for i, _ in enumerate(text_edit_planet):
                        if isinstance(values_planet[i], (int, str)):
                            texts_planet.append(text_edit_planet[i] + values_planet[i])
                        else:
                            texts_planet.append(values_planet[i])
                    texts_merged += texts_planet
                elif int(self.types[self.selected]) == 3:   # star
                    prop_merged = prop_edit_body + prop_edit_star
                    values_star = ["WIP",
                                   "WIP",
                                   "WIP",
                                   "WIP"]
                    texts_star = []
                    for i, _ in enumerate(text_edit_star):
                        texts_star.append(text_edit_star[i] + values_star[i])
                    texts_merged += texts_star
                elif int(self.types[self.selected]) == 4:   # for bh
                    prop_merged = prop_edit_body + prop_edit_bh
                    values_bh = [metric.format_si(self.rad_sc[self.selected], 3)]
                    texts_bh = []
                    for i, _ in enumerate(text_edit_bh):
                        texts_bh.append(text_edit_bh[i] + values_bh[i])
                    texts_merged += texts_bh
                texts_merged.append(text_edit_delete)
                prop_merged.append(3)
                graphics.text_list(screen, texts_merged, (self.r_menu_x_btn, 38), (280, 21), 26, prop=prop_merged)
            
            elif self.right_menu == 5:   # sim config
                texts = []
                for item in self.sim_conf.items():
                    text = str(item[0]) + ": " + str(item[1])
                    texts.append(text)
                prop = [1]*len(texts)
                texts.append(text_load_default)
                prop.append(3)
                graphics.text_list(screen, texts, (self.r_menu_x_btn, 38), (280, 21), 26, prop=prop)
            
            # input value to right ui
            if self.input_value is not None:
                if isinstance(self.input_value, int):
                    y_pos = 38 + self.input_value * 26
                    pygame.draw.rect(screen, rgb.gray2, (self.r_menu_x_btn, y_pos, 280, 21))
                    textinput.graphics(screen, clock, self.fontmd, (self.r_menu_x_btn, y_pos), (280, 21), center=False)
                elif self.input_value is not None:   # if input value is string (for color)
                    y_pos = 38 + int(self.input_value[:-1]) * 26
                    if self.input_value[-1] == "a":
                        x_pos = self.r_menu_x_btn + 58
                    elif self.input_value[-1] == "b":
                        x_pos = self.r_menu_x_btn + 58 + 59
                    else:
                        x_pos = self.r_menu_x_btn + 58 + 2*59
                    pygame.draw.rect(screen, rgb.gray2, (x_pos, y_pos, 53, 21))
                    textinput.graphics(screen, clock, self.fontmd, (x_pos, y_pos), (53, 21), center=False)
                
            
            # top ui
            pygame.draw.rect(screen, rgb.black, (0, 0, self.screen_x, 22))
            pygame.draw.line(screen, rgb.white, (0, 22), (self.screen_x, 22), 1)
            graphics.text(screen, rgb.white, self.fontmd, format_time.to_date(int(self.sim_time/self.ptps), False), (74, 11), center=True)
            pygame.draw.line(screen, rgb.white, (150, 0), (150, 22), 1)
            graphics.buttons_small_h(screen, self.top_ui_imgs, (151, 0))
            
            # ### DEBUG ###
            graphics.text(screen, rgb.gray1, self.fontmd, str(self.mouse_raw), (self.screen_x - 240, 2))
            if self.debug_timer < 10:
                self.debug_timer += 1
                self.physics_debug_time_sum += self.physics_debug_time
            else:
                self.debug_timer = 0
                self.physics_debug_percent = round((self.physics_debug_time_sum/10 * 100) / (1 / clock.get_fps()), 1)
                self.physics_debug_time_sum = 0
            graphics.text(screen, rgb.gray1, self.fontmd, "phys: " + str(self.physics_debug_percent) + "%", (self.screen_x - 150, 2))
            graphics.text(screen, rgb.gray1, self.fontmd, "fps: " + str(int(clock.get_fps())), (self.screen_x - 50, 2))
    
    

    def main(self, screen, clock):
        """Main editor loop"""
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
            self.graphics(screen)
            self.graphics_ui(screen, clock)
            pygame.display.flip()
            clock.tick(60)
        return self.state
