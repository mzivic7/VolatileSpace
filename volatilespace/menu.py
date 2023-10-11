import pygame
import webbrowser
import os
import sys
import shutil
import time
import numpy as np
from ast import literal_eval as leval

from volatilespace import fileops
from volatilespace.graphics import rgb
from volatilespace.graphics import graphics
from volatilespace import editor
from volatilespace import textinput
from volatilespace.graphics import keybinding
try:   # to allow building without numba
    from numba import njit
    numba_avail = True
except ImportError:
    numba_avail = False

graphics = graphics.Graphics()
textinput = textinput.Textinput()


version = "0.4.2"

buttons_main = ["Play - WIP", "Multiplayer - WIP", "Map Editor", "Settings", "About", "Quit"]
buttons_map_sel = ["Open in editor", "Rename", "Delete", "Export"]
buttons_map_ui = ["Back", "New map", "Import map"]
buttons_set_vid = ["Fullscreen", "Resolution", "Antialiasing", "Vsync", "Mouse wrap", "Background stars"]
buttons_set_aud = ["WIP"]
buttons_set_gam = ["Keybindings", "Autosave"]
buttons_set_adv = ["Curve points", "Stars antialiasing", "New star color", "Star clusters", "New clusters", "Numba", "FastMath"]
buttons_set_ui = ["Accept", "Apply", "Cancel", "Load default"]
buttons_about = ["Wiki", "Github", "Itch.io", "Report a bug", "Back"]
buttons_rename = ["Cancel", "Rename"]
buttons_new_map = ["Cancel", "Create"]


class Menu():
    def __init__(self):
        self.state = 1
        self.menu = 0
        self.click = False
        self.first_click = None
        self.click_timer = 0
        self.mouse = [0, 0]
        self.scroll = 0
        self.scroll_sens = 10   # scroll sensitivity
        self.selected_item = 0   # when selecting from list
        self.selected_path = ""
        self.are_you_sure = False
        self.disable_buttons = False
        self.scrollbar_drag = False
        self.keybinding = False   # is keybinding menu active
        self.rename = False   # renaming menu
        self.new_map = False   # new map menu
        
        self.reload_settings()
        self.fonttl = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 42)   # title text font
        self.fonthd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 28)   # heading text font
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        
        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.txt_y_margin = 8  # empty space between text and button edge
        self.btn_h = self.fontbt.get_height() + self.txt_y_margin * 2   # button height from font height
        self.space = 10   # space between buttons
        self.bot_margin = 60
        self.top_margin = 60
        
        self.screen_change = False
        self.res_change = False
        self.restart = False   # restart is needed for settings
        graphics.antial = self.antial
        graphics.set_screen()
        self.gen_map_list()
        self.set_screen()
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        self.main_x = self.screen_x/2 - self.btn_w/2
        self.main_y = self.screen_y/2 - (len(buttons_main) * self.btn_h + (len(buttons_main)-1) * self.space - self.fonttl.get_height())/2
        self.about_x = self.screen_x/2 - self.btn_w/2
        self.about_y = self.screen_y/2 - (len(buttons_about)+2 * self.btn_h + (len(buttons_about)+1) * self.space)/2
        self.settings_section = self.screen_x/4
        self.set_x_1 = self.settings_section/2 - self.btn_w/2
        self.set_x_2 = self.settings_section/2 * 3 - self.btn_w/2
        self.set_x_3 = self.settings_section/2 * 5 - self.btn_w/2
        self.set_x_4 = self.settings_section/2 * 7 - self.btn_w/2
        self.set_x_ui = self.screen_x/2 - (len(buttons_set_ui) * self.btn_w_h + (len(buttons_set_ui)-1) * self.space)/2
        self.map_x_ui = self.screen_x/2 - (len(buttons_map_ui) * self.btn_w_h + (len(buttons_set_ui)-1) * self.space)/2
        self.map_x_1 = self.screen_x/4 - self.btn_w_l/2
        self.map_x_2 = self.screen_x/4 * 3 - self.btn_w/2
        self.map_y_2 = self.screen_y/2 - (len(buttons_map_sel) * self.btn_h + (len(buttons_map_sel)-1) * self.space + self.bot_margin)/2
        self.map_list_size = len(self.maps) * self.btn_h + len(self.maps) * self.space
        self.bot_y_ui = self.screen_y - self.bot_margin
        self.list_limit = self.bot_y_ui - self.top_margin - self.space
        self.ask_x = self.screen_x/2 - (2*self.btn_w_h + self.space)/2
        self.ask_y = self.screen_y/2 + self.space
    
    
    def reload_settings(self):
        """Reload all settings in main menu, should be run every time settings are applied"""
        self.fullscreen = leval(fileops.load_settings("graphics", "fullscreen"))
        self.avail_res = pygame.display.list_modes()
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        try:
            self.selected_res = self.avail_res.index((self.screen_x, self.screen_y))
        except Exception:   # fail-safe repair if resolution is invalid
            self.selected_res = 0   # use maximum resolution
            fileops.save_settings("graphics", "resolution", list(self.avail_res[0]))   # save it to file
            if self.fullscreen is True:
                pygame.display.set_mode((self.avail_res[0]), pygame.FULLSCREEN)
            else:
                pygame.display.set_mode((self.avail_res[0]))
        self.antial = leval(fileops.load_settings("graphics", "antialiasing"))   # global antialiasing
        graphics.set_screen()
        
        # for settings menu only:
        self.vsync = leval(fileops.load_settings("graphics", "vsync"))
        self.mouse_wrap = leval(fileops.load_settings("graphics", "mouse_wrap"))
        self.bg_stars_enable = leval(fileops.load_settings("background", "stars"))
        self.curve_points = int(fileops.load_settings("graphics", "curve_points"))
        self.star_aa = leval(fileops.load_settings("background", "stars_antialiasing"))
        self.new_color = leval(fileops.load_settings("background", "stars_new_color"))
        self.cluster_enable = leval(fileops.load_settings("background", "cluster_enable"))
        self.cluster_new = leval(fileops.load_settings("background", "cluster_new"))
        self.numba = leval(fileops.load_settings("game", "numba"))
        self.fastmath = leval(fileops.load_settings("game", "fastmath"))
        self.autosave_time = int(fileops.load_settings("game", "autosave_time"))
    
    
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
    
    
    ###### --Keys-- ######
    def input_keys(self, e, from_game=False):
        
        if self.rename or self.new_map:
            self.text = textinput.input(e)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.rename = False
                    self.new_map = False
                    self.disable_buttons = False
                elif e.key == pygame.K_RETURN:
                    if self.rename:
                        self.rename = False
                        fileops.rename_map(self.selected_path, self.text)
                        self.gen_map_list()
                    else:
                        self.new_map = False
                        date = time.strftime("%d.%m.%Y %H:%M")
                        path = fileops.new_map(self.text, date)
                        self.gen_map_list()
                    self.disable_buttons = False
        
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                if self.menu == 0:
                    self.state = 0   # close program
                if self.are_you_sure:   # exit from ask window
                    self.are_you_sure = False
                    self.disable_buttons = False
                else:
                    self.menu = 0
                    if from_game:
                        self.state = 2
                if self.scrollbar_drag:
                    self.scrollbar_drag = False
                    self.disable_buttons = False
            elif e.key == pygame.K_F2:
                self.rename = True
                self.disable_buttons = True
                textinput.initial_text(self.maps[self.selected_item, 1], selected=True)
            
            elif e.key == pygame.K_RETURN:
                if self.menu == 3:
                    self.state = 2
                    self.menu = 0
                if self.are_you_sure:
                    try:
                        os.remove(self.selected_path)
                    except Exception:
                        pass
                    self.gen_map_list()
                    self.are_you_sure = False
                    self.disable_buttons = False
            
            # key arrows to move selection in list menu
            elif self.menu == 3:
                if e.key == pygame.K_DOWN:
                    if self.selected_item < len(self.maps)-1:
                        self.selected_item += 1
                        self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                elif e.key == pygame.K_UP:
                    if self.selected_item > 0:
                        self.selected_item -= 1
                        self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
    
    
    
    ###### --Mouse-- ######
    def input_mouse(self, e, from_game=False):
        self.mouse = list(pygame.mouse.get_pos())   # get mouse position
        # left mouse button is clicked
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click = True   # this is to validate that mouse is clicked inside this menu
            
            # scroll bar
            if self.menu == 3:
                scrollable_len = max(0, self.map_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                if scrollable_len != 0:
                    scrollbar_pos = self.scroll * scrollbar_limit / scrollable_len
                else:
                    scrollbar_pos = 0
                scrollbar_y = self.top_margin - self.space + 3 + scrollbar_pos    # calculate scroll bar coords
                scrollbar_x = self.map_x_1 + self.btn_w_l + self.space + 2
                if scrollbar_x <= self.mouse[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse[1]-1 <= scrollbar_y + 40:
                    self.scrollbar_drag = True
                    self.scrollbar_drag_start = self.mouse[1]
                    self.disable_buttons = True
        
        
        # left mouse button is released
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            
            if self.click is True:
                if self.menu == 0:   # main menu
                    y_pos = self.main_y
                    for num, text in enumerate(buttons_main):
                        if self.main_x <= self.mouse[0]-1 <= self.main_x + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            if num+1 != 1 and num+1 != 2:   # skip play, multiplayer
                                self.menu = num+1   # switch to this menu
                                self.click = False   # reset click, to not carry it to next menu
                                if self.menu == 3:   # reload saved maps
                                    self.gen_map_list()
                        y_pos += self.btn_h + self.space   # calculate position for next button
                
                
            if self.menu == 1:   # play
                pass   # WIP #
            
            
            if self.menu == 2:   # multiplayer
                pass   # WIP #
            
            
            if self.click is True:
                if self.menu == 3:   # map editor
                    if self.disable_buttons is False:
                        
                        # maps list
                        if self.top_margin - self.space <= self.mouse[1]-1 <= self.top_margin + self.list_limit:
                            y_pos = self.top_margin - self.scroll
                            for num, text in enumerate(self.maps[:, 1]):
                                if y_pos >= self.top_margin - self.btn_h - self.space and y_pos <= self.top_margin + self.list_limit:    # don't detect outside list area
                                    if self.map_x_1 <= self.mouse[0]-1 <= self.map_x_1 + self.btn_w_l and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                                        self.selected_item = num
                                        self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                                        if self.first_click == num:   # detect double click
                                            self.state = 2
                                            self.menu = 0   # return to main menu instead load menu
                                        self.first_click = num
                                y_pos += self.btn_h + self.space
                        
                        
                        # selected menu
                        y_pos = self.map_y_2
                        for num, text in enumerate(buttons_map_sel):
                            if self.map_x_2 <= self.mouse[0]-1 <= self.map_x_2 + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                                if len(self.maps) != 0:
                                    if num == 0:   # open editor
                                        self.state = 2
                                        self.menu = 0   # return to main menu instead load menu
                                    elif num == 1:   # rename
                                        self.rename = True
                                        self.disable_buttons = True
                                        textinput.initial_text(self.maps[self.selected_item, 1], selected=True)
                                    elif num == 2:   # delete
                                        self.are_you_sure = True
                                        self.disable_buttons = True
                                    elif num == 3:   # export
                                        save_path = fileops.save_file(self.maps[self.selected_item, 1], [("Text Files", "*.ini")])
                                        if save_path != "":
                                            shutil.copy2(self.selected_path, save_path)
                            y_pos += self.btn_h + self.space
                        
                        # ui
                        x_pos = self.map_x_ui
                        for num, text in enumerate(buttons_map_ui):
                            if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and self.bot_y_ui <= self.mouse[1]-1 <= self.bot_y_ui + self.btn_h:
                                if num == 0:   # back
                                    self.menu = 0
                                    self.scroll = 0
                                elif num == 1:   # new map
                                    self.new_map = True
                                    self.disable_buttons = True
                                    textinput.initial_text("New Map", selected=True)
                                elif num == 2:   # import map
                                    file_path = fileops.load_file([("Text Files", "*.ini")])
                                    if file_path != "":
                                        shutil.copy2(file_path, "Maps")
                                        self.gen_map_list()
                            x_pos += self.btn_w_h + self.space
                        
                    # rename and new map
                    if self.rename or self.new_map:
                        x_pos = self.ask_x
                        for num in [0, 1]:
                            if x_pos <= self.mouse[0]-1 <= x_pos+self.btn_w_h and self.ask_y+self.space <= self.mouse[1]-1 <= self.ask_y+self.space+self.btn_h:
                                if num == 0:   # cancel
                                    pass
                                elif num == 1:
                                    if self.rename:
                                        fileops.rename_map(self.selected_path, self.text)
                                        self.gen_map_list()
                                    elif self.new_map:
                                        date = time.strftime("%d.%m.%Y %H:%M")
                                        path = fileops.new_map(self.text, date)
                                        self.gen_map_list()
                                    self.selected_item = np.where(self.maps[:, 1] == self.text)[0][0]
                                self.new_map = False
                                self.rename = False
                                self.disable_buttons = False
                            x_pos += self.btn_w_h + self.space
                        
                    if self.scrollbar_drag is True:   # disable scrollbar_drag when release click
                        self.scrollbar_drag = False
                        self.disable_buttons = False
                    
                    if self.are_you_sure:   # ask to delete
                        x_pos = self.ask_x
                        for num in [0, 1]:
                            if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w_h and self.ask_y <= self.mouse[1]-1 <= self.ask_y + self.btn_h:
                                if num == 0:   # cancel
                                    pass
                                elif num == 1:   # delete
                                    try:
                                        os.remove(self.selected_path)
                                        self.selected_item -= 1
                                    except Exception:
                                        pass
                                    self.gen_map_list()
                                self.are_you_sure = False
                                self.disable_buttons = False
                            x_pos += self.btn_w_h + self.space
            
            
            if self.click is True:
                if self.menu == 4:   # settings
                    
                    # graphics
                    x_pos = self.set_x_1
                    y_pos = self.top_margin
                    for num, text in enumerate(buttons_set_vid):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # fullscreen
                                self.fullscreen = not self.fullscreen
                                self.screen_change = not self.screen_change
                            elif num == 1:   # resolution
                                if x_pos <= self.mouse[0]-1 <= x_pos + 40:   # minus
                                    self.selected_res += 1   # +1 because avail_res is from largest to smallest
                                    self.res_change = True
                                elif x_pos+self.btn_w-40 <= self.mouse[0]-1 <= x_pos + self.btn_w:   # plus
                                    self.selected_res -= 1
                                    self.res_change = True
                                if self.selected_res < 0:   # if selected res is negative
                                    self.selected_res = len(self.avail_res) - 1   # return it to min res
                                if self.selected_res > len(self.avail_res) - 1:   # if selected res is out of range
                                    self.selected_res = 0   # return it to max res
                            elif num == 2:   # antialiasing
                                self.antial = not self.antial
                            elif num == 3:   # vsync
                                self.vsync = not self.vsync
                                self.restart = True
                            elif num == 4:   # mouse wrap
                                self.mouse_wrap = not self.mouse_wrap
                            elif num == 5:   # background stars
                                self.bg_stars_enable = not self.bg_stars_enable
                        y_pos += self.btn_h + self.space
                    
                    # audio
                    x_pos = self.set_x_2
                    y_pos = self.top_margin
                    for num, text in enumerate(buttons_set_aud):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            if num == 0:
                                pass
                        y_pos += self.btn_h + self.space
                    
                    # game
                    x_pos = self.set_x_3
                    y_pos = self.top_margin
                    for num, text in enumerate(buttons_set_gam):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # Keybindings
                                self.keybinding = True
                            elif num == 1:   # autosave
                                if x_pos <= self.mouse[0]-1 <= x_pos + 40:   # minus
                                    if self.autosave_time < 15:
                                        self.autosave_time -= 1
                                    else:
                                        self.autosave_time -= 5
                                    if self.autosave_time < 0:   # if autosave time is 0, it is disabled
                                        self.autosave_time = 0
                                if x_pos+self.btn_w-40 <= self.mouse[0]-1 <= x_pos + self.btn_w:   # plus
                                    if self.autosave_time < 10:
                                        self.autosave_time += 1
                                    else:
                                        self.autosave_time += 5
                                    if self.autosave_time > 90:   # limit to 90min
                                        self.autosave_time = 90
                        y_pos += self.btn_h + self.space
                    
                    # advanced
                    x_pos = self.set_x_4
                    y_pos = self.top_margin
                    for num, text in enumerate(buttons_set_adv):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # curve points
                                if x_pos <= self.mouse[0]-1 <= x_pos + 40:   # minus
                                    self.curve_points -= 25
                                    if self.curve_points < 0:
                                        self.curve_points = 0
                                if x_pos+self.btn_w-40 <= self.mouse[0]-1 <= x_pos + self.btn_w:   # plus
                                    self.curve_points += 25
                            elif num == 1:   # stars antialiasing
                                self.star_aa = not self.star_aa
                            elif num == 2:   # stars new color
                                self.new_color = not self.new_color
                            elif num == 3:   # cluster enable
                                self.cluster_enable = not self.cluster_enable
                            elif num == 4:   # cluster new
                                self.cluster_new = not self.cluster_new
                            elif num == 5:   # numba
                                if numba_avail:
                                    self.numba = not self.numba
                                    self.restart = True
                            elif num == 6:   # FastMath
                                if self.numba:
                                    self.fastmath = not self.fastmath
                                    self.restart = True
                        y_pos += self.btn_h + self.space
                    
                    # ui
                    x_pos = self.set_x_ui
                    for num, text in enumerate(buttons_set_ui):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and self.bot_y_ui <= self.mouse[1]-1 <= self.bot_y_ui + self.btn_h:
                            if num == 0 or num == 1:   # accept/apply
                                if num == 0:
                                    self.menu = 0
                                    if from_game:
                                        self.state = 2
                                fileops.save_settings("graphics", "fullscreen", self.fullscreen)
                                fileops.save_settings("graphics", "resolution", list(self.avail_res[self.selected_res]))
                                fileops.save_settings("graphics", "antialiasing", self.antial)
                                fileops.save_settings("graphics", "vsync", self.vsync)
                                fileops.save_settings("graphics", "mouse_wrap", self.mouse_wrap)
                                fileops.save_settings("graphics", "curve_points", self.curve_points)
                                fileops.save_settings("background", "stars", self.bg_stars_enable)
                                fileops.save_settings("background", "stars_antialiasing", self.star_aa)
                                fileops.save_settings("background", "stars_new_color", self.new_color)
                                fileops.save_settings("background", "cluster_enable", self.cluster_enable)
                                fileops.save_settings("background", "cluster_new", self.cluster_new)
                                fileops.save_settings("game", "numba", self.numba)
                                fileops.save_settings("game", "fastmath", self.fastmath)
                                fileops.save_settings("game", "autosave_time", self.autosave_time)
                                # change windowed/fullscreen
                                if self.screen_change is True:
                                    
                                    pygame.display.toggle_fullscreen()
                                    self.set_screen()
                                    graphics.set_screen()
                                    self.screen_change = False
                                # change resolution
                                if self.res_change is True:
                                    if self.fullscreen is True:   # if previously in fullscreen, stay in fullscreen
                                        pygame.display.set_mode((self.avail_res[self.selected_res]), pygame.FULLSCREEN)
                                    else:
                                        pygame.display.set_mode((self.avail_res[self.selected_res]))
                                    self.set_screen()
                                    graphics.set_screen()
                                    self.res_change = False
                            
                            elif num == 2:   # cancel
                                self.reload_settings()
                                self.menu = 0
                                if from_game:
                                    self.state = 2
                                self.restart = False
                                
                            elif num == 3:   # load default
                                fileops.delete_settings()
                                self.restart = True
                        x_pos += self.btn_w_h + self.space
            
            
            if self.click is True:
                if self.menu == 5:   # about
                    y_pos = self.about_y
                    for num, text in enumerate(buttons_about):
                        if self.about_x <= self.mouse[0]-1 <= self.about_x + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # wiki
                                webbrowser.open(r"https://github.com/mzivic7/VolatileSpace/blob/main/documentation/wiki.md")
                            elif num == 1:   # github
                                webbrowser.open(r"https://github.com/mzivic7/VolatileSpace")
                            elif num == 2:   # itch.io
                                webbrowser.open(r"https://mzivic.itch.io/volatile-space")
                            elif num == 3:   # report bug
                                webbrowser.open(r"https://github.com/mzivic7/VolatileSpace/issues")
                            elif num == 4:   # back
                                self.menu = 0
                        y_pos += self.btn_h + self.space
                
            if self.menu == 6:   # quit
                self.state = 0
            
            self.click = False
        
        
        # moving scrollbar with cursor
        if self.scrollbar_drag is True:
            if self.menu == 3:
                # calculate scroll from scrollbar position
                scrollbar_pos = self.mouse[1] - self.top_margin
                scrollable_len = max(0, self.map_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                self.scroll = scrollable_len * scrollbar_pos / scrollbar_limit
                if self.scroll < 0:
                    self.scroll = 0
                elif self.scroll > max(0, self.map_list_size - self.list_limit):
                    self.scroll = max(0, self.map_list_size - self.list_limit)
        
        
        if e.type == pygame.MOUSEWHEEL:
            if self.menu == 3:
                if self.scrollbar_drag is False:
                    # scrolling inside list area
                    if self.map_x_1-self.space <= self.mouse[0]-1 <= self.map_x_1+self.btn_w_l+self.space+16 and self.top_margin-self.space <= self.mouse[1]-1 <= self.top_margin+self.list_limit:
                        self.scroll -= e.y * self.scroll_sens
                        if self.scroll < 0:
                            self.scroll = 0
                        elif self.scroll > max(0, self.map_list_size - self.list_limit):
                            self.scroll = max(0, self.map_list_size - self.list_limit)
        
        graphics.update_mouse(self.mouse, self.click, self.disable_buttons)
    
    
    
    ###### --Graphics-- ######
    def graphics_ui(self, screen, clock):
        screen.fill((0, 0, 0))   # color screen black
        
        # main menu
        if self.menu == 0:
            graphics.text(screen, rgb.white, self.fonttl, "Volatile Space", (self.screen_x/2, self.main_y - self.fonttl.get_height()), True)
            graphics.buttons_vertical(screen, buttons_main, (self.main_x, self.main_y), [5, 5, None, None, None, None])
        
        
        # play
        elif self.menu == 1:
            pass   # WIP #
        
        
        # multiplayer
        elif self.menu == 2:
            pass   # WIP #
        
        
        # map editor
        elif self.menu == 3:
            # maps list
            graphics.buttons_list(screen, self.maps[:, 1], (self.map_x_1, self.top_margin), self.list_limit, self.scroll, self.selected_item)
            
            # selected menu
            if len(self.maps) != 0:
                selected_name = self.maps[self.selected_item, 1]
                selected_date = "Last edited: " + self.maps[self.selected_item, 2]
                
            else:
                selected_name = "No saved maps"
                selected_date = ""
            graphics.text(screen, rgb.white, self.fontbt, selected_name, (self.map_x_2 + self.btn_w/2, self.map_y_2 - self.btn_h), True)
            graphics.text(screen, rgb.gray, self.fontmd, selected_date, (self.map_x_2 + self.btn_w/2, self.map_y_2 - self.btn_h/2+3), True)
            graphics.buttons_vertical(screen, buttons_map_sel, (self.map_x_2, self.map_y_2))
            
            # connector
            if len(self.maps) != 0:
                graphics.connector(screen, buttons_map_sel, (self.map_x_1, self.top_margin), (self.map_x_2, self.map_y_2), self.bot_margin, self.scroll, self.maps, self.selected_item)
            
            # ui
            graphics.buttons_horizontal(screen, buttons_map_ui, (self.map_x_ui, self.bot_y_ui))
            
            # ask to delete
            if self.are_you_sure is True:
                ask_del = "Are you sure you want to permanently delete:"
                graphics.ask(screen, ask_del, self.maps[self.selected_item, 1], "Delete", (self.ask_x, self.ask_y), True)
            
            # rename
            if self.rename or self.new_map:
                border_rect = [self.ask_x-self.space, self.ask_y-40-self.btn_h, self.btn_w_h*2+3*self.space, self.btn_h+40+self.btn_h+2*self.space]
                bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
                pygame.draw.rect(screen, rgb.black, bg_rect)
                pygame.draw.rect(screen, rgb.white, border_rect, 1)
                if self.rename:
                    menu_title = "Rename"
                    buttons = buttons_rename
                else:
                    menu_title = "New Map"
                    buttons = buttons_new_map
                graphics.text(screen, rgb.white, self.fontbt, menu_title, (self.screen_x/2,  self.ask_y-20-self.btn_h), True)
                textinput.graphics(screen, clock, self.fontbt, (self.ask_x, self.ask_y-self.btn_h), (self.btn_w_h*2+self.space, self.btn_h))
                graphics.buttons_horizontal(screen, buttons, (self.ask_x, self.ask_y+self.space), safe=True)
            
            # double click counter   # not graphics related, but must be outside of input functions
            if self.first_click is not None:
                self.click_timer += clock.get_fps() / 60
                if self.click_timer >= 0.5 * 60:
                    self.first_click = None
                    self.click_timer = 0
        
        
        # settings
        elif self.menu == 4:
            
            # video
            graphics.text(screen, rgb.white, self.fonthd, "Video", (self.settings_section/2, 30), True)
            buttons_set_vid[1] = str(self.avail_res[self.selected_res]).strip("(").strip(")").replace(", ", "x")
            prop_1 = [int(self.fullscreen), 3, int(self.antial), int(self.vsync), int(self.mouse_wrap), int(self.bg_stars_enable)]
            graphics.buttons_vertical(screen, buttons_set_vid, (self.set_x_1, self.top_margin), prop_1)
            
            # audio
            graphics.text(screen, rgb.white, self.fonthd, "Audio", (self.settings_section/2 * 3, 30), True)
            prop_2 = [5]
            graphics.buttons_vertical(screen, buttons_set_aud, (self.set_x_2, self.top_margin), prop_2)
            
            # game
            graphics.text(screen, rgb.white, self.fonthd, "Game", (self.settings_section/2 * 5, 30), True)
            prop_3 = [None, 3]
            buttons_set_gam[1] = "Autosave: " + str(self.autosave_time) + "min"
            graphics.buttons_vertical(screen, buttons_set_gam, (self.set_x_3, self.top_margin), prop_3)
            
            # advanced
            graphics.text(screen, rgb.white, self.fonthd, "Advanced", (self.settings_section/2 * 7, 30), True)
            buttons_set_adv[0] = "Curve: " + str(self.curve_points)
            if numba_avail:
                numba_button = int(self.numba)
            else:
                numba_button = 5
            if numba_avail and self.numba:
                fastmath_button = int(self.fastmath)
            else:
                fastmath_button = 5
            prop_4 = [3, int(self.star_aa), int(self.new_color), int(self.cluster_enable), int(self.cluster_new), numba_button, fastmath_button]
            graphics.buttons_vertical(screen, buttons_set_adv, (self.set_x_4, self.top_margin), prop_4)
            
            # ui
            graphics.buttons_horizontal(screen, buttons_set_ui, (self.set_x_ui, self.bot_y_ui))
            
            # warnings
            if self.fullscreen is True and self.selected_res != 0:
                graphics.text(screen, rgb.red, self.fontmd, "Fullscreen mode may not work when in lower resolutions.", (self.screen_x/2, self.bot_y_ui-28), True)
            if self.restart is True:
                graphics.text(screen, rgb.red, self.fontmd, "Restart is required for changes to take effect.", (self.screen_x/2, self.bot_y_ui-12), True)
            
            # keybinding:
            if self.keybinding is True:
                keybinding.main(screen, clock)
                self.keybinding = False
        
        
        # about
        elif self.menu == 5:
            graphics.text(screen, rgb.white, self.fontbt, "Created by: Marko Zivic", (self.screen_x/2, self.about_y - self.btn_h*2), True)
            graphics.text(screen, rgb.white, self.fontbt, "Version: " + version, (self.screen_x/2, self.about_y - self.btn_h), True)
            graphics.buttons_vertical(screen, buttons_about, (self.about_x, self.about_y), [2, 2, 2, 2, None])
        
        
        # version number
        graphics.text(screen, rgb.gray1, self.fontmd, "v" + version, (self.screen_x - 50, self.screen_y - 20))
    
    
    
    def main(self, screen, clock, from_game=False):
        run = True
        if from_game is True:
            self.menu = 4   # go directly to settings
        while run:
            for e in pygame.event.get():
                self.input_keys(e, from_game)
                self.input_mouse(e, from_game)
                if self.state != 1:
                    state = self.state
                    self.state = 1   # this allows returning back to main menu
                    if from_game is True:
                        return 2   # go back to game
                    return state
                if e.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            self.graphics_ui(screen, clock)
            pygame.display.flip()
            clock.tick(60)
        return self.state
