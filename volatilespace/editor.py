import pygame
import math
import numpy as np
import os
import sys
import time
import datetime
from configparser import ConfigParser
from ast import literal_eval as leval

from volatilespace import fileops
from volatilespace import physics_engine
from volatilespace.graphics import rgb
from volatilespace.graphics import graphics
from volatilespace.graphics import bg_stars

physics = physics_engine.Physics()
graphics = graphics.Graphics()
bg_stars = bg_stars.Bg_Stars()


buttons_pause_menu = ["Resume", "Save map", "Load map", "Settings", "Quit without saving", "Save and Quit"]
buttons_save = ["Cancel", "Save", "New save"]
buttons_load = ["Cancel", "Load"]


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
        self.disable_gui = False
        self.disable_labels = False
        self.menu = None
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
        self.space = 10   # space between buttons
        self.file_path = ""   # path to currently active file
        self.selected_path = ""   # path to selected file
        self.gen_map_list()
        self.reload_settings()
        graphics.antial = self.antial
        
        # simulation related
        self.ptps = 59   # divisor to convert simulation time to real time (it is not 60 because userevent timer is rounded to 17ms)
        self.zoom = 0.15   # initial zoom value
        self.key_sens = 0.02   # sensitivity when pressing or holding wasd buttons
        self.select_sens = 5   # how many pixels are tolerable for mouse to move while selecting body
        self.drag_sens = 0.02   # drag sensitivity when inserting body
        self.warp_range = [1, 2, 3, 4, 5, 10, 50, 100]   # all possible warps, by order
        self.warp_index = 0   # current warp from warp_rang
        self.sim_time = 0   # simulation time
        self.pause = False   # program paused
        self.insert_body = False   # is body being inserted
        self.move = False    # move view mode
        self.body_del = False   # which body will be deleted
        self.selected = False   # select mode
        self.direction = False   # keyboard buttons wasd
        self.follow = False   # follow selected body
        self.first = True   # is this first iterration
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

        
        self.new_mass_init = 5   # initial mass for custom spawned objects
        self.new_density_init = 1   # initial density for custom spawned objects
        self.new_mass = self.new_mass_init   # set initial mass for custom spawned objects
        self.new_density = self.new_density_init   # set initial density for custom spawned objects
        self.new_color = (100, 100, 100)   # set initial color for custom spawned objects
        
        self.offset_old = np.array([self.offset_x, self.offset_y])
        self.grid_enable = False   # background grid
        self.grid_mode = 0   # grid mode: 0 - global, 1 - selected body, 2 - parent
        
        bg_stars.set_screen()   # load pygame stuff in classes after pygame init has finished
        graphics.set_screen()
        
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        self.ask_x = self.screen_x/2 - (2*self.btn_w_h + self.space)/2
        self.ask_y = self.screen_y/2 + self.space
        self.pause_x = self.screen_x/2 - self.btn_w/2
        self.pause_y = self.screen_y/2 - (len(buttons_pause_menu) * self.btn_h + (len(buttons_pause_menu)-1) * self.space)/2
        graphics.update_buttons(self.btn_w, self.btn_w_h, self.btn_w_l, self.btn_h)
        self.pause_max_y = self.btn_h*len(buttons_pause_menu) + self.space*(len(buttons_pause_menu)+1)
        self.maps_x = self.screen_x/2 - self.btn_w_l/2
        self.maps_max_y = self.screen_y - 200
        self.list_limit = self.maps_max_y - self.btn_h - self.space
        self.maps_y = (self.screen_y - self.maps_max_y)/2
        self.maps_x_ui = self.maps_x - self.space
        self.maps_y_ui = self.maps_y + self.list_limit + self.space
        self.map_list_size = len(self.maps) * self.btn_h + len(self.maps) * self.space
        
    
    def gen_map_list(self):
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
    

    ###### --Reload settings-- ######
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
            if self.fullscreen is True:
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
        return [x_on_screen, y_on_screen]
    
    def sim_coords(self, coords_on_screen):
        """Converts from screen coords to sim coords. Adds zoom, view move, and moves origin from bottom-left to up-left"""
        x_in_sim = coords_on_screen[0] / self.zoom - self.offset_x + self.zoom_x   # correction for zoom, screen movement offset
        y_in_sim = -(coords_on_screen[1] - self.screen_y) / self.zoom - self.offset_y + self.zoom_y
        # y_on_screen = y_on_screen - screen_y   move origin from bottom-left to up-left. This is implemented in above line
        return [x_in_sim, y_in_sim]
    
    
    
    ###### --Load system-- ######
    def load_system(self, system):
        self.sim_name, self.sim_time, self.mass, self.density, self.position, self.velocity, self.color = fileops.load_system(system)
        self.sim_time *= self.ptps   # convert from seconds to userevent iterations
        physics.load_system(self.mass, self.density, self.position, self.velocity, self.color)   # add it to physics class
        self.file_path = system   # this path will be used for load/save
        self.disable_input = False
        self.disable_gui = False
        self.disable_labels = False
        self.gen_map_list()
        
        # userevent may not been run in first iteration, but this values are needed in graphics section:
        self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()   # get body information
        self.first = True
    
    
    
    ###### --Keys-- ######
    def input_keys(self, e):
        if self.state != 2:   # when returning to editor menu
            self.state = 2   # update state
        if e.type == pygame.KEYDOWN:   # if any key is pressed:
            if e.key == pygame.K_ESCAPE:
                if self.scrollbar_drag is True:
                    self.scrollbar_drag = False
                    self.ask = None
                if self.ask is None:
                    if self.menu is not None:
                        self.menu = None
                        self.pause_menu = True
                    elif self.pause_menu is True:
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
                    self.pause = False
            
            if self.disable_input is False:
                if e.key == self.keys["interactive_pause"]:
                    if self.pause is False:
                        self.pause = True   # if it is not paused, pause it
                    else:
                        self.pause = False  # if it is paused, unpause it
                
                elif e.key == self.keys["focus_home"]:
                    self.follow = False   # disable follow
                    self.focus_point([0, 0], 0.5)   # return to (0,0) coordinates
                    # self.zoom = 1   # reset zoom
                    # self.zoom_x, self.zoom_y = 0, 0   # reset zoom offset
                    
                elif e.key == self.keys["follow_selected_body"]:
                    self.follow = not self.follow   # toggle follow
                
                elif e.key == self.keys["toggle_background_grid"]:
                    self.grid_enable = not self.grid_enable
                
                elif e.key == self.keys["cycle_grid_modes"]:
                    if self.grid_enable is True:
                        self.grid_mode += 1   # cycle grid modes (0 - global, 1 - selected body, 2 - parent)
                        if self.grid_mode >= 3:
                            self.grid_mode = 0
                
                elif e.key == self.keys["screenshot"]:
                    if not os.path.exists("Screenshots"):
                        os.mkdir("Screenshots")
                    self.screenshot = True
                
                elif e.key == self.keys["toggle_ui_visibility"]:
                    self.disable_gui = not self.disable_gui
                
                elif e.key == self.keys["toggle_labels_visibility"]:
                    self.disable_labels = not self.disable_labels
                
                elif e.key == self.keys["quicksave"]:
                    self.pause = True
                    self.ask = "save"
                    self.disable_input = True
                
                elif e.key == self.keys["load_quicksave"]:
                    self.pause = True
                    self.ask = "load"
                    self.disable_input = True
                
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
                
                if self.selected is not False:   # if there is selected body, allow changing its velocity with wasd
                    if e.key == self.keys["forward"]:
                        self.direction = "up"   # to what direction velocity is added
                    if e.key == self.keys["backward"]:
                        self.direction = "down"
                    if e.key == self.keys["left"]:
                        self.direction = "left"
                    if e.key == self.keys["right"]:
                        self.direction = "right"
        
        if e.type == pygame.KEYUP and (e.key == pygame.K_w or e.key == pygame.K_s or e.key == pygame.K_a or e.key == pygame.K_d):
            self.direction = False   # when wasd key is released, clear direction to which velocity is added
        
        if self.direction is not False:   # add velocity to specific direction
            mass, density, temp, position, velocity, colors, size, rad_sc = physics.get_bodies()   # get body velocity to be increased
            if self.direction == "up":   # new_velocity = old_velocity + key_sensitivity
                physics.set_body_vel(self.selected, [velocity[self.selected, 0], velocity[self.selected, 1] + self.key_sens])   # set new velocity
            if self.direction == "down":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0], velocity[self.selected, 1] - self.key_sens])
            if self.direction == "left":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0] - self.key_sens, velocity[self.selected, 1]])
            if self.direction == "right":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0] + self.key_sens, velocity[self.selected, 1]])
    
    
    
    ###### --Mouse-- ######
    def input_mouse(self, e):
        self.mouse_raw = list(pygame.mouse.get_pos())   # get mouse position
        self.mouse = list((self.mouse_raw[0]/self.zoom, -(self.mouse_raw[1] - self.screen_y)/self.zoom))   # mouse position on zoomed screen
        # y coordinate in self.mouse is negative for easier applying in formula to check if mouse is inside circle
        
        # left mouse button: move, select
        if self.disable_input is False:
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:   # is clicked
                self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
                self.move = True   # enable view move
                self.mouse_old = self.mouse   # initial mouse position for movement
                self.mouse_raw_old = self.mouse_raw   # initial mouse position for movement
                        
            if e.type == pygame.MOUSEBUTTONUP and e.button == 1:   # is released:
                self.move = False   # disable move move
                mouse_move = math.dist(self.mouse_raw, self.mouse_raw_old)   # mouse move dist
                self.select_toggle = False
                if mouse_move < self.select_sens:   # if mouse moved less than n pixels:
                    for self.body, self.body_pos in enumerate(self.position):   # for each body:
                        # if mouse is inside body radius on its location: (body_x - mouse_x)**2 + (body_y - mouse_y)**2 < radius**2
                        if sum(np.square(self.body_pos - self.sim_coords(self.mouse_raw))) < (self.size[self.body])**2:
                            self.selected = self.body  # this body is selected
                            self.select_toggle = True   # do not exit select mode
                    if self.select_toggle is False:   # if inside select mode
                        self.selected = False   # exit select mode
        
        if self.disable_input is False:
            # right mouse button: insert
            if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:   # is clicked
                self.insert_body = True   # start inserting body
                self.new_position = self.sim_coords(self.mouse_raw)   # first position
            if e.type == pygame.MOUSEBUTTONUP and e.button == 3 and self.insert_body is True:   # is released
                self.insert_body = False   # end inserting body
                drag_position = self.sim_coords(self.mouse_raw)   # second position
                distance = math.dist(self.new_position, drag_position) * self.zoom   # distance
                angle = math.atan2(drag_position[1] - self.new_position[1], drag_position[0] - self.new_position[0])   # angle
                new_acc = distance * self.drag_sens   # decrease acceleration to reasonable value
                new_acc_x = new_acc * math.cos(angle)   # separate acceleration components by axes
                new_acc_y = new_acc * math.sin(angle)
                new_velocity = [new_acc_x, new_acc_y]   # new velocity
                physics.add_body(self.new_mass, self.new_density, self.new_position, new_velocity, self.new_color)   # add new body to class
                self.new_mass = self.new_mass_init   # reset initial new mass
            
            # mouse wheel
            if e.type == pygame.MOUSEWHEEL and self.insert_body is True:
                if self.new_mass > 1:   # keep mass positive
                    self.new_mass += e.y   # change mass
            if e.type == pygame.MOUSEWHEEL and self.insert_body is False:   # change zoom
                if self.zoom > self.zoom_step or e.y == 1:   # prevent zooming below zoom_step, zoom can't be 0, but allow zoom to increase
                    self.zoom_step = self.zoom / 10   # calculate zoom_step from current zoom
                    self.zoom += e.y * self.zoom_step   # add value to zoom by scrolling on mouse
                    self.zoom_x += (self.screen_x / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
                    self.zoom_y += (self.screen_y / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_y / (self.zoom * 2))
                    # these values are added only to displayed objects, traces... But not to real position
        
        if e.type == pygame.MOUSEWHEEL and (self.menu == 0 or self.menu == 1):
            if self.scrollbar_drag is False:
                # scrolling inside list area
                if self.maps_x-self.space <= self.mouse_raw[0]-1 <= self.maps_x+self.btn_w_l+self.space+16 and self.maps_y-self.space <= self.mouse_raw[1]-1 <= self.maps_y+self.list_limit:
                    self.scroll -= e.y * self.scroll_sens
                    if self.scroll < 0:
                        self.scroll = 0
                    elif self.scroll > max(0, self.map_list_size - self.list_limit):
                        self.scroll = max(0, self.map_list_size - self.list_limit)
    
    
    def ui_mouse(self, e):
        graphics.update_mouse(self.mouse_raw, self.click, self.disable_input)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click = True
            # scroll bar
            if self.menu == 0 or self.menu == 1:
                scrollable_len = max(0, self.map_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                if scrollable_len != 0:
                    scrollbar_pos = self.scroll * scrollbar_limit / scrollable_len
                else:
                    scrollbar_pos = 0
                scrollbar_x = self.maps_x + self.btn_w_l + self.space + 2    # calculate scroll bar coords
                scrollbar_y = self.maps_y - self.space + 3 + scrollbar_pos
                if scrollbar_x <= self.mouse_raw[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse_raw[1]-1 <= scrollbar_y + 40:
                    self.scrollbar_drag = True
                    self.scrollbar_drag_start = self.mouse[1]
                    self.ask = True   # dirty shortcut to disable safe buttons
        
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.click is True:
                
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
                                self.gen_map_list()
                            elif num == 2:   # load
                                self.menu = 1
                                self.pause_menu = False
                                self.gen_map_list()
                            elif num == 3:   # settings
                                self.state = 4   # go directly to main menu settings, but be able to return here
                            elif num == 4:   # quit
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.pause = False
                            elif num == 5:   # save and quit
                                base_color = physics.get_base_color()
                                date = time.strftime("%d.%m.%Y %H:%M")
                                fileops.save_system(self.file_path, self.sim_name, date, self.sim_time/self.ptps, self.mass, self.density, self.position, self.velocity, base_color)
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.pause = False
                        y_pos += self.btn_h + self.space
                
                # disable scrollbar_drag when release click
                elif self.scrollbar_drag is True:
                    self.scrollbar_drag = False
                    self.ask = None
                
                # save
                elif self.menu == 0:
                    # maps list
                    if self.maps_y - self.space <= self.mouse_raw[1]-1 <= self.maps_y + self.list_limit:
                        y_pos = self.maps_y - self.scroll
                        for num, text in enumerate(self.maps[:, 1]):
                            if y_pos >= self.maps_y - self.btn_h - self.space and y_pos <= self.maps_y + self.list_limit:    # don't detect outside list area
                                if self.maps_x <= self.mouse_raw[0]-1 <= self.maps_x + self.btn_w_l and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                                    self.selected_item = num
                                    self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                                    if self.first_click == num:   # detect double click
                                        self.ask = "save"
                                    self.first_click = num
                            y_pos += self.btn_h + self.space
                    
                    x_pos = self.maps_x_ui
                    for num, text in enumerate(buttons_save):
                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h_3 and self.maps_y_ui <= self.mouse_raw[1]-1 <= self.maps_y_ui + self.btn_h:
                            if num == 0:   # cancel
                                self.menu = None
                                self.pause_menu = True
                            elif num == 1:   # save
                                self.ask = "save"
                            elif num == 2:   # new save
                                date = time.strftime("%d.%m.%Y %H:%M")
                                new_name = "New Map from " + date   # ### TODO ###
                                path = fileops.new_map(new_name, date)
                                base_color = physics.get_base_color()
                                fileops.save_system(path, new_name, date, self.sim_time/self.ptps, self.mass, self.density, self.position, self.velocity, base_color)
                                self.gen_map_list()
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
                
                # ask
                if self.ask is not None:
                    x_pos = self.ask_x
                    for num in [0, 1]:
                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h and self.ask_y <= self.mouse_raw[1]-1 <= self.ask_y + self.btn_h:
                            if num == 0:   # cancel
                                pass
                            elif num == 1:   # delete
                                if self.ask == "load":
                                    if os.path.exists(self.selected_path):
                                        self.sim_name, self.sim_time, self.mass, self.density, self.position, self.velocity, self.color = fileops.load_system(self.selected_path)
                                        self.sim_time *= self.ptps   # convert from seconds to userevent iterations
                                        physics.load_system(self.mass, self.density, self.position, self.velocity, self.color)
                                        self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
                                        self.file_path = self.selected_path   # change currently active file
                                        graphics.timed_text_init(rgb.gray, self.fontmd, "Map loaded successfully", (self.screen_x/2, self.screen_y-70), 2, True)
                                if self.ask == "save":
                                    base_color = physics.get_base_color()
                                    date = time.strftime("%d.%m.%Y %H:%M")
                                    fileops.save_system(self.selected_path, self.sim_name, date, self.sim_time/self.ptps, self.mass, self.density, self.position, self.velocity, base_color)
                                    self.file_path = self.selected_path
                                    graphics.timed_text_init(rgb.gray, self.fontmd, "Map saved successfully", (self.screen_x/2, self.screen_y-70), 2, True)
                            if self.menu is not None:
                                self.menu = None
                                self.pause_menu = True
                            else:
                                self.disable_input = False
                                self.pause = False
                            self.ask = None
                        x_pos += self.btn_w_h + self.space
            self.click = False
        
        
        # moving scrollbar with cursor
        if self.scrollbar_drag is True:
            if self.menu == 0 or self.menu == 1:
                # calculate scroll from scrollbar position
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
        if e.type == pygame.USEREVENT:   # event for calculations
            if self.pause is False:   # if it is not paused:
                for num in range(self.warp):
                    physics.gravity()   # do gravity physics
                    physics.body_size()   # calculate bodies radius
                    physics.body_temp()   # calculate bodies temperature
                    physics.black_hole()   # check for black holes
                    # get bodies information
                    self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
                    
                    body_del = physics.inelastic_collision()   # collisions
                    if body_del is not False:   # if there is collision
                        self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()  # get bodies information after deletion
                        if body_del == self.selected:   # if selected body is deleted:
                            self.selected = False   # exit from select mode
                        if body_del < self.selected:   # if body before selected one is deleted
                            self.selected -= 1   # on list move selected body back
                        self.direction = False   # reset wasd if not false
                    
                    self.sim_time += 1   # iterate sim_time
                    
                    if self.first is True:   # this is run only once at userevent start
                        self.first = False   # do not run it again
                        self.focus_point([0, 0], 0.5)   # initial zoom and point
                        self.selected = 0   # select body
                        self.follow = True   # follow it
        
        physics.kepler_basic()   # calculate basic keplerian elements
        self.semi_major, self.semi_minor, self.coi, self.parents = physics.get_body_orbits()   # get basic keplerian elements
        self.colors = physics.body_color()   # calculate colors from temperature
    
    
    
    ###### --Graphics-- ######
    def graphics(self, screen, clock):
        screen.fill((0, 0, 0))   # color screen black
        
        
        # follow body (this must be before drawing objects to prevent them from vibrating when moving)
        if self.follow is True and self.selected is not False:   # if follow mode is enabled
            self.offset_x = - self.position[self.selected, 0] + self.screen_x / 2   # follow selected body
            self.offset_y = - self.position[self.selected, 1] + self.screen_y / 2
        
        
        # screen movement
        if self.move is True:   # this is not in userevent to allow moving while paused
            if self.mouse_fix_x is True:   # when mouse jumps from one edge to other:
                self.mouse_old[0] = self.mouse[0]   # don't calculate that as mouse movement
                self.mouse_fix_x = False
            if self.mouse_fix_y is True:
                self.mouse_old[1] = self.mouse[1]
                self.mouse_fix_y = False
            
            mouse_move = math.dist((self.mouse_raw[0], self.mouse_raw[1]), (self.mouse_raw_old[0], self.mouse_raw_old[1]))   # distance
            self.offset_x += self.mouse[0] - self.mouse_old[0]   # add mouse movement to offset
            self.offset_y += self.mouse[1] - self.mouse_old[1]
            # save mouse position for next iteration to get movement
            # print position of view, here is not added zoom offset, this shows real position, y axis is inverted
            if not self.disable_gui:
                graphics.text(screen, rgb.white, self.fontmd, "Pos: X:" + str(int(self.offset_x - self.screen_x / 2)) + "; Y:" + str(-int(self.offset_y - self.screen_y / 2)), (300, 2))
            if mouse_move > self.select_sens:   # stop following if mouse distance is more than n pixels
                self.follow = False   # stop following selected body
            
            if self.mouse_wrap is True:
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
        if self.bg_stars_enable is True:
            offset_diff = self.offset_old - np.array([self.offset_x, self.offset_y])   # movement vector in one iterration
            offset_diff = offset_diff * min(self.zoom, 3)   # add zoom to speed calculation and limit zoom
            self.offset_old = np.array([self.offset_x, self.offset_y])
            speed = math.sqrt(offset_diff.dot(offset_diff))/3   # speed as movement vector magnitude
            direction = math.atan2(offset_diff[1], offset_diff[0])   # movement vector angle from atan2
            bg_stars.draw_bg(screen, speed, direction, self.zoom)
        
        
        # background lines grid
        if self.grid_enable is True:
            if self.grid_mode == 0:   # grid mode: home
                origin = self.screen_coords([0, 0])
            if self.selected is not False:
                if self.grid_mode == 1:      # grid mode: selected body
                    if self.follow is False:
                        origin = self.screen_coords(self.position[self.selected])
                    else:   # When following body, origin is in center of screen
                        origin = [(- self.zoom_x + self.screen_x/2) * self.zoom, self.screen_y - (- self.zoom_y + self.screen_y/2) * self.zoom]
                if self.grid_mode == 2:   # grid mode: parent of selected body
                    origin = self.screen_coords(self.position[self.parents[self.selected]])
            else:
                origin = self.screen_coords([0, 0])
            graphics.draw_grid(screen, self.grid_mode, origin, self.zoom)
        
        
        # draw orbit curve lines
        curve_x, curve_y = physics.curve()   # calculate all curves
        for body in range(len(self.mass)):   # for each body:
            if body != 0:   # skip most massive body
                curve = np.column_stack(self.screen_coords(np.stack([curve_x[body], curve_y[body]])))   # get line coords on screen
                line_color = np.where(self.colors[body] > 255, 255, self.colors[body])   # get line color and limit values to top 255
                graphics.draw_lines(screen, tuple(line_color), curve, 2)   # draw that line

        
        # draw bodies
        for body in range(len(self.mass)):   # for all bodies:
            body_size = self.size[body]   # get body size
            body_color = tuple(self.colors[body])   # get color
            graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.position[body]), body_size * self.zoom)   # draw circles
            
        
        # inserting new body
        if self.insert_body is True:
            # calculate distance to current mouse position
            current_position = [(self.mouse_raw[0]/self.zoom) - self.offset_x + self.zoom_x,
                                - ((self.mouse_raw[1] - self.screen_y)/self.zoom) - self.offset_y + self.zoom_y]
            drag_distance = math.dist(self.new_position, current_position) * self.zoom
            if not self.disable_gui:
                graphics.text(screen, rgb.white, self.fontmd, "Pos: X:" + str(round(self.new_position[0])) + "; Y:" + str(round(self.new_position[1])), (300, 2))
                graphics.text(screen, rgb.white, self.fontmd, "Mass: " + str(round(self.new_mass)), (470, 2))
                graphics.text(screen, rgb.white, self.fontmd, "Acc: " + str(round(drag_distance * self.drag_sens, 2)), (560, 2))
            new_volume = self.new_mass / self.new_density   # get size of new body from mass
            new_size = (3 * new_volume / (4 * 3.14))**(1/3)   # calculate radius from volume
            # draw new body before released
            graphics.draw_circle_fill(screen, self.new_color, self.screen_coords(self.new_position), new_size * self.zoom)
            # draw line connecting body and release point
            graphics.draw_line(screen, rgb.red, self.screen_coords(self.new_position), (self.mouse_raw[0], self.mouse_raw[1]), 1)
        
        
        # select body
        if self.selected is not False:
            parent = self.parents[self.selected]      # get selected body parent
            body_pos = self.position[self.selected, :]      # get selected body position
            ecc, periapsis, apoapsis, pe_d, ap_d, distance, period, pe_t, ap_t, orb_angle, speed_orb, speed_hor, speed_vert = physics.kepler_advanced(self.selected)   # get advanced kepler parameters for selected body
            
            # circles
            if not self.disable_labels:
                graphics.draw_circle(screen, rgb.cyan, self.screen_coords(body_pos), self.size[self.selected] * self.zoom + 4, 2)   # selection circle
            if self.size[self.selected] < self.coi[self.selected]:   # if there is circle of influence, draw it
                graphics.draw_circle(screen, rgb.gray1, self.screen_coords(body_pos), self.coi[self.selected] * self.zoom + 4, 1)
            if self.selected != 0:   # skip most massive body, draw parent circle
                graphics.draw_circle(screen, rgb.red1, self.screen_coords(self.position[parent]), self.size[parent] * self.zoom + 4, 1)
                if parent != 0:   # if parent is not most massive body, draw parent circle of influence
                    graphics.draw_circle(screen, rgb.red1, self.screen_coords(self.position[parent]), self.coi[parent] * self.zoom + 4, 1)
            
            # ap and pe
            if not self.disable_labels:
                if not ecc > 1:   # if orbit is not parabola or hyperbola
                    if ecc != 0:   # if orbit is not circle
                        # periapsis location marker, text: distance and time to it
                        pe_scr = self.screen_coords(periapsis)   # periapsis screen coords
                        graphics.draw_circle_fill(screen, rgb.lime1, pe_scr, 3)   # periapsis marker
                        graphics.text(screen, rgb.lime1, self.fontsm, "Periapsis: " + str(round(pe_d, 1)), (pe_scr[0], pe_scr[1] + 7), True)
                        graphics.text(screen, rgb.lime1, self.fontsm, "T - " + str(datetime.timedelta(seconds=round(pe_t/self.ptps))), (pe_scr[0], pe_scr[1] + 17), True)
                    
                    if ecc < 1:   # if orbit is ellipse
                        # apoapsis location marker, text: distance and time to it
                        ap_scr = self.screen_coords(apoapsis)   # apoapsis with zoom and offset
                        graphics.draw_circle_fill(screen, rgb.lime1, ap_scr, 3)   # apoapsis marker
                        graphics.text(screen, rgb.lime1, self.fontsm, "Apoapsis: " + str(round(ap_d, 1)), (ap_scr[0], ap_scr[1] + 7), True)
                        graphics.text(screen, rgb.lime1, self.fontsm, "T - " + str(datetime.timedelta(seconds=round(ap_t/self.ptps))), (ap_scr[0], ap_scr[1] + 17), True)
        
        
        # print basic data
        if not self.disable_gui:
            graphics.timed_text(screen, clock)   # timed text on screen
            graphics.text(screen, rgb.white, self.fontmd, str(datetime.timedelta(seconds=round(self.sim_time/self.ptps))), (2, 2))
            if self.pause is True:   # if paused
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
            graphics.text(screen, rgb.gray, self.fontmd, str(self.mouse_raw), (self.screen_x - 100, self.screen_y - 60))
            graphics.text(screen, rgb.gray, self.fontmd, "(" + str(int(self.sim_coords(self.mouse_raw)[0])) + ", " + str(int(self.sim_coords(self.mouse_raw)[1])) + ")", (self.screen_x - 100, self.screen_y - 40))
            graphics.text(screen, rgb.gray, self.fontmd, "fps: " + str(int(clock.get_fps())), (self.screen_x - 60, self.screen_y - 20))
    
    
    
    ###### --Menus-- ######
    def gui(self, screen, clock):
        
        # pause menu
        if self.pause_menu is True:
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
            graphics.buttons_list(screen, self.maps[:, 1], (self.maps_x, self.maps_y), self.list_limit, self.scroll, self.selected_item, safe=not (bool(self.ask)))
            graphics.buttons_horizontal(screen, buttons_save, (self.maps_x_ui, self.maps_y_ui), alt_width=self.btn_w_h_3, safe=not (bool(self.ask)))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
        
        # load menu
        elif self.menu == 1:
            border_rect = [self.maps_x-2*self.space, self.maps_y-2*self.space, self.btn_w_l+4*self.space + 16, self.maps_max_y+3*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            graphics.buttons_list(screen, self.maps[:, 1], (self.maps_x, self.maps_y), self.list_limit, self.scroll, self.selected_item, safe=not (bool(self.ask)))
            graphics.buttons_horizontal(screen, buttons_load, (self.maps_x - self.space, self.maps_y_ui), alt_width=self.btn_w_h_2, safe=not (bool(self.ask)))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
        
        if not self.disable_gui:   # disabled menus
            pass
        
        # asking to load/save
        if self.ask == "load":
            ask_txt = "Loading will overwrite unsaved changes."
            graphics.ask(screen, ask_txt, self.sim_name, "Load", (self.ask_x, self.ask_y))
        elif self.ask == "save":
            ask_txt = "Are you sure you want to overwrite this save:"
            graphics.ask(screen, ask_txt, self.sim_name, "Save", (self.ask_x, self.ask_y))
        
        # screenshot
        if self.screenshot is True:
            date = time.strftime("%Y-%m-%d %H-%M-%S")
            screenshot_path = "Screenshots/Screenshot from " + date + ".png"
            pygame.image.save(screen, screenshot_path)
            if not self.disable_gui:
                graphics.timed_text_init(rgb.gray, self.fontmd, "Screenshot saved at: " + screenshot_path, (self.screen_x/2, self.screen_y-70), 2, True)
            self.screenshot = False
        
        # double click counter   # not graphics related, but must be outside of input functions
        if self.first_click is not None:
            self.click_timer += clock.get_fps() / 60
            if self.click_timer >= 0.5 * 60:
                self.first_click = None
                self.click_timer = 0
    
    
    
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
            self.graphics(screen, clock)
            self.gui(screen, clock)
            pygame.display.flip()
            clock.tick(60)
        return self.state
