import importlib.util
import os
import shutil
import sys
import time
import webbrowser

import numpy as np
import pygame

from volatilespace import peripherals, textinput
from volatilespace.graphics import graphics, keybinding, rgb
from volatilespace.utils import responsive_blocking

numba_avail = bool(importlib.util.find_spec("numba"))

graphics = graphics.Graphics()
textinput = textinput.Textinput()


version = "0.5.2"

buttons_main = [
    "Play",
    "Multiplayer - WIP",
    "Map Editor",
    "Settings",
    "About",
    "Quit",
]
buttons_play_ui = ["Back", "New game", "Import game"]
buttons_play_sel = ["Play", "Rename", "Delete", "Export"]
buttons_new_game = ["Back", "New game", "Import map"]
buttons_map_sel = ["Open in editor", "Rename", "Delete", "Export"]
buttons_map_ui = ["Back", "New map", "Import map"]
buttons_set_vid = [
    "Fullscreen",
    "Resolution",
    "Antialiasing",
    "Vsync",
    "Mouse warp",
    "Background stars",
]
buttons_set_aud = ["WIP"]
buttons_set_gam = ["Keybindings", "Autosave:"]
buttons_set_adv = [
    "Curve:",
    "New star color",
    "Star clusters",
    "New clusters",
    "Numba",
    "FastMath",
]
buttons_set_ui = ["Accept", "Apply", "Cancel", "Load default"]
buttons_about = ["Wiki", "Github", "Itch.io", "Report a bug", "Back"]
buttons_rename = ["Cancel", "Rename"]
buttons_new_map = ["Cancel", "Create"]


class Menu():
    """Menu class"""
    def __init__(self):
        self.state = 1
        self.menu = 0
        self.click = False
        self.first_click = None
        self.click_timer = 0
        self.mouse = [0, 0]
        self.scroll = 0
        self.scroll_maps = 0
        self.scroll_sensitivity = 20
        self.selected_item = 0
        self.selected_path = ""
        self.selected_ng_item = 0   # selecting in new game menu
        self.selected_ng_path = ""
        self.are_you_sure = False
        self.disable_buttons = False
        self.scrollbar_drag = False
        self.scrollbar_drag_start = 0
        self.keybinding = False
        self.rename = False
        self.new_map = False
        self.new_game = False
        self.text = ""

        self.reload_settings()
        self.fonttl = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 42)   # title text font
        self.fonthd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 28)   # heading text font
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font

        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.btn_w_h_3 = (self.btn_w_l + 16)/3   # fits 3 btn in width of list button
        self.txt_y_margin = 8  # empty space between text and button edge
        self.btn_h = self.fontbt.get_height() + self.txt_y_margin * 2   # button height from font height
        self.space = 10   # space between buttons
        self.bot_margin = 60
        self.top_margin = 60

        self.screen_change = False
        self.res_change = False
        self.restart = False
        self.no_filedialog = False
        graphics.antial = self.antial
        graphics.set_screen()
        self.gen_map_list()
        self.gen_game_list()
        self.set_screen()

    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
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
        self.game_list_size = len(self.games) * self.btn_h + len(self.games) * self.space
        self.bot_y_ui = self.screen_y - self.bot_margin
        self.list_limit = self.bot_y_ui - self.top_margin - self.space
        self.ask_x = self.screen_x/2 - (2*self.btn_w_h + self.space)/2
        self.ask_y = self.screen_y/2 + self.space
        self.maps_x = self.screen_x/2 - self.btn_w_l/2
        self.maps_max_y = self.screen_y - 200
        self.maps_list_limit = self.maps_max_y - self.btn_h - self.space
        self.maps_y = (self.screen_y - self.maps_max_y)/2
        self.maps_x_ui = self.maps_x - self.space
        self.maps_y_ui = self.maps_y + self.maps_list_limit + self.space
        self.maps_list_size = len(self.maps) * self.btn_h + len(self.maps) * self.space


    def reload_settings(self):
        """Reload all settings in main menu, should be run every time settings are applied"""
        self.fullscreen = peripherals.load_settings("graphics", "fullscreen")
        self.avail_res = pygame.display.list_modes()
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        try:
            self.selected_res = self.avail_res.index((self.screen_x, self.screen_y))
        except Exception:   # fail-safe if resolution is invalid
            self.selected_res = 0   # use maximum resolution
            peripherals.save_settings("graphics", "resolution", list(self.avail_res[0]))
            if self.fullscreen is True:
                pygame.display.set_mode((self.avail_res[0]), pygame.FULLSCREEN)
            else:
                pygame.display.set_mode((self.avail_res[0]))
        self.antial = peripherals.load_settings("graphics", "antialiasing")
        graphics.set_screen()

        # for settings menu only
        self.vsync = peripherals.load_settings("graphics", "vsync")
        self.mouse_warp = peripherals.load_settings("graphics", "mouse_warp")
        self.bg_stars_enable = peripherals.load_settings("background", "stars")
        self.curve_points = int(peripherals.load_settings("graphics", "curve_points"))
        self.new_color = peripherals.load_settings("background", "stars_new_color")
        self.cluster_enable = peripherals.load_settings("background", "cluster_enable")
        self.cluster_new = peripherals.load_settings("background", "cluster_new")
        self.numba = peripherals.load_settings("game", "numba")
        self.fastmath = peripherals.load_settings("game", "fastmath")
        self.autosave_time = int(peripherals.load_settings("game", "autosave_time"))


    def gen_map_list(self):
        """Generate list of maps and select currently active file"""
        self.maps = peripherals.gen_map_list()
        self.map_list_size = len(self.maps) * self.btn_h + len(self.maps) * self.space
        if len(self.maps) != 0:
            if self.selected_item >= len(self.maps):
                self.selected_item = len(self.maps) - 1
            self.selected_path = "Maps/" + self.maps[self.selected_item, 0]

        # limit text size
        for num, text in enumerate(self.maps[:, 1]):
            new_text = graphics.limit_text(text, self.fontbt, self.btn_w_l)
            if new_text != text:
                self.maps[num, 1] = new_text


    def gen_game_list(self):
        """Generate list of games and select currently active file"""
        self.games = peripherals.gen_game_list()
        self.game_list_size = len(self.games) * self.btn_h + len(self.games) * self.space
        if len(self.games) != 0:
            if self.selected_item >= len(self.games):
                self.selected_item = len(self.games) - 1
            self.selected_path = "Saves/" + self.games[self.selected_item, 0]

        # limit text size
        for num, text in enumerate(self.games[:, 1]):
            new_text = graphics.limit_text(text, self.fontbt, self.btn_w_l)
            if new_text != text:
                self.games[num, 1] = new_text


    def input_keys(self, e, from_game=False):
        """Keyboard input"""
        if self.rename or self.new_map or self.new_game:
            self.text = textinput.input(e)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.rename = False
                    self.new_map = False
                    self.new_game = False
                    self.disable_buttons = False
                elif e.key == pygame.K_RETURN:
                    if self.rename:
                        if self.menu == 1:
                            peripherals.rename_game(self.selected_path, self.text)
                            self.gen_game_list()
                        else:
                            self.rename = False
                            peripherals.rename_map(self.selected_path, self.text)
                            self.gen_map_list()
                        self.rename = False
                    else:
                        date = time.strftime("%d.%m.%Y %H:%M")
                        if self.menu == 2:
                            _ = peripherals.new_map(self.text, date)
                            self.gen_map_list()
                            self.new_map = False
                        if self.new_game:
                            self.new_game = False
                            game_path = self.selected_ng_path.replace("Maps/", "Saves/").replace(".ini", "") + " " + date + ".ini"
                            game_name = self.maps[self.selected_ng_item, 1] + " " + date
                            shutil.copy2(self.selected_ng_path, game_path)    # copy map to games
                            peripherals.rename_game(game_path, game_name)
                            self.selected_path = game_path   # select new created game
                            self.state = 3
                            self.menu = 0
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
                if self.menu == 1:
                    textinput.initial_text(self.games[self.selected_item, 1], "rename_game", selected=True)
                else:
                    textinput.initial_text(self.maps[self.selected_item, 1], "rename_editor", selected=True)

            elif e.key == pygame.K_RETURN:
                if self.are_you_sure:
                    try:
                        os.remove(self.selected_path)
                        self.selected_item -= 1
                        self.selected_item = max(self.selected_item, 0)
                    except Exception:
                        pass
                    self.gen_map_list()
                    self.gen_game_list()
                    self.are_you_sure = False
                    self.disable_buttons = False
                elif self.menu == 1:
                    self.state = 3
                    self.menu = 0
                elif self.menu == 3:
                    self.state = 2
                    self.menu = 0

            # key arrows to move selection in list menu
            elif self.menu in [1, 3]:
                if e.key == pygame.K_DOWN:
                    if self.selected_item < len(self.maps)-1:
                        self.selected_item += 1
                        if self.menu == 3:
                            self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                        else:
                            self.selected_path = "Saves/" + self.maps[self.selected_item, 0]
                elif e.key == pygame.K_UP:
                    if self.selected_item > 0:
                        self.selected_item -= 1
                        if self.menu == 3:
                            self.selected_path = "Maps/" + self.maps[self.selected_item, 0]
                        else:
                            self.selected_path = "Saves/" + self.maps[self.selected_item, 0]


    def input_mouse(self, e, from_game=False):
        """Mouse input"""
        self.mouse = list(pygame.mouse.get_pos())
        # left mouse button is clicked
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click = True   # this is to validate that mouse is clicked inside this menu

            # scroll bar
            if self.menu in [1, 3] and not self.new_game:
                if self.menu == 1:
                    list_size = self.game_list_size
                else:
                    list_size = self.map_list_size
                scrollable_len = max(0, list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                if scrollable_len != 0:
                    scrollbar_pos = self.scroll * scrollbar_limit / scrollable_len
                else:
                    scrollbar_pos = 0
                scrollbar_y = self.top_margin - self.space + 3 + scrollbar_pos
                scrollbar_x = self.map_x_1 + self.btn_w_l + self.space + 2
                if scrollbar_x <= self.mouse[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse[1]-1 <= scrollbar_y + 40:
                    self.scrollbar_drag = True
                    self.scrollbar_drag_start = self.mouse[1]
                    self.disable_buttons = True

            # scroll bar
            if self.new_game:
                scrollable_len = max(0, self.maps_list_size - self.maps_list_limit)
                scrollbar_limit = self.maps_list_limit - 40 + 4
                if scrollable_len != 0:
                    scrollbar_pos = self.scroll_maps * scrollbar_limit / scrollable_len
                else:
                    scrollbar_pos = 0
                scrollbar_x = self.maps_x + self.btn_w_l + self.space + 2
                scrollbar_y = self.maps_y - self.space + 3 + scrollbar_pos
                if scrollbar_x <= self.mouse[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse[1]-1 <= scrollbar_y + 40:
                    self.scrollbar_drag = True
                    self.scrollbar_drag_start = self.mouse[1]

        # left mouse button is released
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:

            if self.click is True:
                if self.menu == 0:   # main menu
                    y_pos = self.main_y
                    for num, _ in enumerate(buttons_main):
                        if self.main_x <= self.mouse[0]-1 <= self.main_x + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            self.menu = num+1   # switch to this menu
                            self.click = False   # reset click, to not carry it to next menu
                            if self.menu == 3:   # editor
                                self.gen_map_list()
                                self.scroll = 0
                            if self.menu == 1:   # play
                                self.gen_game_list()
                            self.scroll = 0
                        y_pos += self.btn_h + self.space

            if self.click is True:
                if self.menu == 1:   # play
                    if self.disable_buttons is False:

                        # games list
                        if self.top_margin - self.space <= self.mouse[1]-1 <= self.top_margin + self.list_limit:
                            y_pos = self.top_margin - self.scroll
                            for num, _ in enumerate(self.games[:, 1]):
                                if y_pos >= self.top_margin - self.btn_h - self.space and y_pos <= self.top_margin + self.list_limit:    # don't detect outside list area
                                    if self.map_x_1 <= self.mouse[0]-1 <= self.map_x_1 + self.btn_w_l and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                                        self.selected_item = num
                                        self.selected_path = "Saves/" + self.games[self.selected_item, 0]
                                        if self.first_click == num:   # detect double click
                                            self.state = 3
                                            self.menu = 0   # return to main menu instead load menu
                                        self.first_click = num
                                y_pos += self.btn_h + self.space

                        # selected menu
                        y_pos = self.map_y_2
                        for num, _ in enumerate(buttons_play_sel):
                            if self.map_x_2 <= self.mouse[0]-1 <= self.map_x_2 + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                                if len(self.games) != 0:
                                    if num == 0:   # play
                                        self.state = 3
                                        self.menu = 0
                                    elif num == 1:   # rename
                                        self.rename = True
                                        self.disable_buttons = True
                                        textinput.initial_text(self.games[self.selected_item, 1], "rename_game", selected=True)
                                    elif num == 2:   # delete
                                        self.are_you_sure = True
                                        self.disable_buttons = True
                                    elif num == 3:   # export
                                        save_path = responsive_blocking(
                                            peripherals.export_file,
                                            (self.games[self.selected_item, 1], ["*.ini"]),
                                        )
                                        if save_path:
                                            if save_path == "ERROR_NO_DIALOG":
                                                self.no_filedialog = True
                                            else:
                                                shutil.copy2(self.selected_path, save_path)
                            y_pos += self.btn_h + self.space

                        # ui
                        x_pos = self.map_x_ui
                        for num, text in enumerate(buttons_play_ui):
                            if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and self.bot_y_ui <= self.mouse[1]-1 <= self.bot_y_ui + self.btn_h:
                                if num == 0:   # back
                                    self.menu = 0
                                    self.scroll = 0
                                elif num == 1:   # new game
                                    self.new_game = True
                                    self.disable_buttons = True
                                    self.scroll_maps = 0
                                    self.selected_ng_item = 0
                                    if len(self.maps):
                                        self.selected_ng_path = "Maps/" + self.maps[0, 0]
                                    else:
                                        self.selected_ng_path = None
                                elif num == 2:   # import game
                                    file_path = responsive_blocking(peripherals.import_file, (["*.ini"], ))
                                    if file_path:
                                        if file_path == "ERROR_NO_DIALOG":
                                            self.no_filedialog = True
                                        else:
                                            shutil.copy2(file_path, "Saves")
                                            self.gen_game_list()
                            x_pos += self.btn_w_h + self.space

                    # rename
                    if self.rename:
                        x_pos = self.ask_x
                        for num in [0, 1]:
                            if x_pos <= self.mouse[0]-1 <= x_pos+self.btn_w_h and self.ask_y+self.space <= self.mouse[1]-1 <= self.ask_y+self.space+self.btn_h:
                                if num == 0:   # cancel
                                    pass
                                elif num == 1:
                                    if self.rename:
                                        peripherals.rename_game(self.selected_path, self.text)
                                    self.selected_item = np.where(self.games[:, 1] == self.text)[0][0]
                                self.rename = False
                                self.disable_buttons = False
                            x_pos += self.btn_w_h + self.space

                    # new game
                    if self.new_game and not self.scrollbar_drag:
                        # maps list
                        if self.maps_y - self.space <= self.mouse[1]-1 <= self.maps_y + self.maps_list_limit:
                            y_pos = self.maps_y - self.scroll_maps
                            for num, text in enumerate(self.maps[:, 1]):
                                if y_pos >= self.maps_y - self.btn_h - self.space and y_pos <= self.maps_y + self.maps_list_limit:    # don't detect outside list area
                                    if self.maps_x <= self.mouse[0]-1 <= self.maps_x + self.btn_w_l and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                                        self.selected_ng_item = num
                                        self.selected_ng_path = "Maps/" + self.maps[self.selected_ng_item, 0]
                                        if self.first_click == num:   # detect double click
                                            try:
                                                date = time.strftime("%d-%m-%Y %H-%M")
                                                game_path = self.selected_ng_path.replace("Maps/", "Saves/").replace(".ini", "") + " " + date + ".ini"
                                                game_name = self.maps[self.selected_ng_item, 1] + " " + date
                                                shutil.copy2(self.selected_ng_path, game_path)    # copy map to games
                                                peripherals.rename_game(game_path, game_name)
                                                self.selected_path = game_path   # select new created game
                                                self.state = 3
                                                self.new_game = False
                                                self.disable_buttons = False
                                                self.menu = 0
                                            except Exception:
                                                pass
                                            self.click = False
                                        self.first_click = num
                                y_pos += self.btn_h + self.space

                        x_pos = self.maps_x_ui
                        for num, text in enumerate(buttons_new_game):
                            if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w_h_3 and self.maps_y_ui <= self.mouse[1]-1 <= self.maps_y_ui + self.btn_h:
                                if num == 0:   # cancel
                                    self.new_game = False
                                    self.disable_buttons = False
                                elif num == 1:   # play
                                    try:
                                        date = time.strftime("%d-%m-%Y %H-%M")
                                        game_path = self.selected_ng_path.replace("Maps/", "Saves/").replace(".ini", "") + " " + date + ".ini"
                                        game_name = self.maps[self.selected_ng_item, 1] + " " + date
                                        shutil.copy2(self.selected_ng_path, game_path)    # copy map to games
                                        peripherals.rename_game(game_path, game_name)
                                        self.selected_path = game_path   # select new created game
                                        self.state = 3
                                        self.menu = 0
                                        self.new_game = False
                                        self.disable_buttons = False
                                        self.click = False
                                    except Exception:
                                        pass
                                elif num == 2:   # import map
                                    file_path = responsive_blocking(peripherals.import_file, (["*.ini"], ))
                                    if file_path:
                                        if file_path == "ERROR_NO_DIALOG":
                                            self.no_filedialog = True
                                        else:
                                            shutil.copy2(file_path, "Maps")
                                            self.gen_map_list()
                                            file_path = None
                            x_pos += self.btn_w_h_3 + self.space

                    if self.scrollbar_drag is True:   # disable scrollbar_drag when release click
                        self.scrollbar_drag = False
                        if not self.new_game:
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
                                        self.selected_item = max(self.selected_item, 0)
                                    except Exception:
                                        pass
                                    self.gen_game_list()
                                self.are_you_sure = False
                                self.disable_buttons = False
                            x_pos += self.btn_w_h + self.space

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
                                            self.menu = 0
                                        self.first_click = num
                                y_pos += self.btn_h + self.space

                        # selected menu
                        y_pos = self.map_y_2
                        for num, text in enumerate(buttons_map_sel):
                            if self.map_x_2 <= self.mouse[0]-1 <= self.map_x_2 + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                                if len(self.maps) != 0:
                                    if num == 0:   # open editor
                                        self.state = 2
                                        self.menu = 0
                                    elif num == 1:   # rename
                                        self.rename = True
                                        self.disable_buttons = True
                                        textinput.initial_text(self.maps[self.selected_item, 1], "rename_editor", selected=True)
                                    elif num == 2:   # delete
                                        self.are_you_sure = True
                                        self.disable_buttons = True
                                    elif num == 3:   # export
                                        save_path = responsive_blocking(
                                            peripherals.export_file,
                                            (self.maps[self.selected_item, 1], ["*.ini"]),
                                        )
                                        if save_path:
                                            if save_path == "ERROR_NO_DIALOG":
                                                self.no_filedialog = True
                                            else:
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
                                    textinput.initial_text("New Map", "new_map", selected=True)
                                elif num == 2:   # import map
                                    file_path = responsive_blocking(peripherals.import_file, (["*.ini"], ))
                                    if file_path:
                                        if file_path == "ERROR_NO_DIALOG":
                                            self.no_filedialog = True
                                        else:
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
                                        peripherals.rename_map(self.selected_path, self.text)
                                        self.gen_map_list()
                                    elif self.new_map:
                                        date = time.strftime("%d.%m.%Y %H:%M")
                                        _ = peripherals.new_map(self.text, date)
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
                                        self.selected_item = max(self.selected_item, 0)
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
                                if self.selected_res < 0:   # limit resolution
                                    self.selected_res = len(self.avail_res) - 1
                                if self.selected_res > len(self.avail_res) - 1:
                                    self.selected_res = 0
                            elif num == 2:   # antialiasing
                                self.antial = not self.antial
                            elif num == 3:   # vsync
                                self.vsync = not self.vsync
                                self.restart = True
                            elif num == 4:   # mouse warp
                                self.mouse_warp = not self.mouse_warp
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
                                    self.autosave_time = max(self.autosave_time, 0)
                                if x_pos+self.btn_w-40 <= self.mouse[0]-1 <= x_pos + self.btn_w:   # plus
                                    if self.autosave_time < 10:
                                        self.autosave_time += 1
                                    else:
                                        self.autosave_time += 5
                                    self.autosave_time = min(self.autosave_time, 90)
                        y_pos += self.btn_h + self.space

                    # advanced
                    x_pos = self.set_x_4
                    y_pos = self.top_margin
                    for num, text in enumerate(buttons_set_adv):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # curve points
                                if x_pos <= self.mouse[0]-1 <= x_pos + 40:   # minus
                                    self.curve_points -= 25
                                    self.curve_points = max(self.curve_points, 0)
                                if x_pos+self.btn_w-40 <= self.mouse[0]-1 <= x_pos + self.btn_w:   # plus
                                    self.curve_points += 25
                            elif num == 1:   # stars new color
                                self.new_color = not self.new_color
                            elif num == 2:   # cluster enable
                                self.cluster_enable = not self.cluster_enable
                            elif num == 3:   # cluster new
                                self.cluster_new = not self.cluster_new
                            elif num == 4:   # numba
                                if numba_avail:
                                    self.numba = not self.numba
                                    self.restart = True
                            elif num == 5:   # FastMath
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
                                peripherals.save_settings("graphics", "fullscreen", self.fullscreen)
                                peripherals.save_settings("graphics", "resolution", list(self.avail_res[self.selected_res]))
                                peripherals.save_settings("graphics", "antialiasing", self.antial)
                                peripherals.save_settings("graphics", "vsync", self.vsync)
                                peripherals.save_settings("graphics", "mouse_warp", self.mouse_warp)
                                peripherals.save_settings("graphics", "curve_points", self.curve_points)
                                peripherals.save_settings("background", "stars", self.bg_stars_enable)
                                peripherals.save_settings("background", "stars_new_color", self.new_color)
                                peripherals.save_settings("background", "cluster_enable", self.cluster_enable)
                                peripherals.save_settings("background", "cluster_new", self.cluster_new)
                                peripherals.save_settings("game", "numba", self.numba)
                                peripherals.save_settings("game", "fastmath", self.fastmath)
                                peripherals.save_settings("game", "autosave_time", self.autosave_time)
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
                                peripherals.delete_settings()
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
            if self.menu in [1, 3] and not self.new_game:
                # scrollbar for play and editor
                if self.menu == 1:
                    list_size = self.game_list_size
                else:
                    list_size = self.map_list_size
                scrollbar_pos = self.mouse[1] - self.top_margin
                scrollable_len = max(0, list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                self.scroll = scrollable_len * scrollbar_pos / scrollbar_limit
                if self.scroll < 0:
                    self.scroll = 0
                elif self.scroll > max(0, list_size - self.list_limit):
                    self.scroll = max(0, list_size - self.list_limit)

            if self.new_game:
                # scrollbar for new game
                scrollbar_pos = self.mouse[1] - self.maps_y
                scrollable_len = max(0, self.maps_list_size - self.maps_list_limit)
                scrollbar_limit = self.maps_list_limit - 40 + 4
                self.scroll_maps = scrollable_len * scrollbar_pos / scrollbar_limit
                if self.scroll_maps < 0:
                    self.scroll_maps = 0
                elif self.scroll_maps > max(0, self.maps_list_size - self.maps_list_limit):
                    self.scroll_maps = max(0, self.maps_list_size - self.maps_list_limit)

        if e.type == pygame.MOUSEWHEEL:
            if self.menu in [1, 3]:
                if self.menu == 1:
                    list_size = self.game_list_size
                else:
                    list_size = self.map_list_size
                if self.scrollbar_drag is False:
                    if self.map_x_1-self.space <= self.mouse[0]-1 <= self.map_x_1+self.btn_w_l+self.space+16 and self.top_margin-self.space <= self.mouse[1]-1 <= self.top_margin+self.list_limit:
                        self.scroll -= e.y * self.scroll_sensitivity
                        if self.scroll < 0:
                            self.scroll = 0
                        elif self.scroll > max(0, list_size - self.list_limit):
                            self.scroll = max(0, list_size - self.list_limit)

        graphics.update_mouse(self.mouse, self.click, self.disable_buttons)


    def graphics_ui(self, screen, clock):
        """Draw GUI menus"""
        screen.fill((0, 0, 0))   # color screen black

        # main menu
        if self.menu == 0:
            graphics.text(
                screen, rgb.white, self.fonttl,
                "Volatile Space",
                (self.screen_x/2, self.main_y - self.fonttl.get_height()), True,
            )
            graphics.buttons_vertical(screen, buttons_main, (self.main_x, self.main_y), [None, 5, None, None, None, None])


        # play
        elif self.menu == 1:
            # games list
            graphics.buttons_list(screen, self.games[:, 1], (self.map_x_1, self.top_margin), self.list_limit, self.scroll, self.selected_item)

            # selected menu
            if len(self.games) != 0:
                selected_name = self.games[self.selected_item, 1]
                selected_date = "Last played: " + self.games[self.selected_item, 2]

            else:
                selected_name = "No saved games"
                selected_date = ""
            graphics.text(
                screen, rgb.white, self.fontbt,
                selected_name,
                (self.map_x_2 + self.btn_w/2, self.map_y_2 - self.btn_h), True,
            )
            graphics.text(
                screen, rgb.gray, self.fontmd,
                selected_date,
                (self.map_x_2 + self.btn_w/2, self.map_y_2 - self.btn_h/2+3), True,
            )
            graphics.buttons_vertical(screen, buttons_play_sel, (self.map_x_2, self.map_y_2))

            # connector
            if len(self.games) != 0:
                graphics.connector(screen, buttons_play_sel, (self.map_x_1, self.top_margin), (self.map_x_2, self.map_y_2), self.bot_margin, self.scroll, self.games, self.selected_item)

            # ui
            graphics.buttons_horizontal(screen, buttons_play_ui, (self.map_x_ui, self.bot_y_ui))

            # ask to delete
            if self.are_you_sure is True:
                ask_del = "Are you sure you want to permanently delete:"
                graphics.ask(screen, ask_del, self.games[self.selected_item, 1], "Delete", (self.ask_x, self.ask_y), True)

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
                graphics.text(
                    screen, rgb.white, self.fontbt,
                    menu_title,
                    (self.screen_x/2,  self.ask_y-20-self.btn_h), True,
                )
                textinput.graphics(
                    screen, clock, self.fontbt,
                    (self.ask_x, self.ask_y-self.btn_h),
                    (self.btn_w_h*2+self.space, self.btn_h),
                )
                graphics.buttons_horizontal(screen, buttons, (self.ask_x, self.ask_y+self.space), safe=True)

            if self.new_game:
                border_rect = [self.maps_x-2*self.space, self.maps_y-2*self.space, self.btn_w_l+4*self.space + 16, self.maps_max_y+3*self.space]
                bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
                pygame.draw.rect(screen, rgb.black, bg_rect)
                if len(self.maps):
                    graphics.buttons_list(screen, self.maps[:, 1], (self.maps_x, self.maps_y), self.maps_list_limit, self.scroll_maps, self.selected_ng_item, safe=not self.scrollbar_drag)
                    prop = None
                else:
                    graphics.buttons_list(screen, ["NO MAPS AVAILABLE"], (self.maps_x, self.maps_y), self.maps_list_limit, self.scroll_maps, 1, safe=not self.scrollbar_drag)
                    prop = [None, 5, None]
                graphics.buttons_horizontal(screen, buttons_new_game, (self.maps_x - self.space, self.maps_y_ui), alt_width=self.btn_w_h_3, prop=prop, safe=not self.scrollbar_drag)
                pygame.draw.rect(screen, rgb.white, border_rect, 1)

            if self.no_filedialog:
                graphics.text(
                    screen, rgb.red, self.fontmd,
                    "Zenity or KDialog packages are requied to display file dialog.",
                    (self.screen_x/2, self.bot_y_ui-21),
                )

            # double click counter (not graphics related, but must be outside of input functions)
            if self.first_click is not None:
                self.click_timer += clock.get_fps() / 60
                if self.click_timer >= 0.5 * 60:
                    self.first_click = None
                    self.click_timer = 0

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
            graphics.text(
                screen, rgb.white, self.fontbt,
                selected_name,
                (self.map_x_2 + self.btn_w/2, self.map_y_2 - self.btn_h), True,
            )
            graphics.text(
                screen, rgb.gray, self.fontmd,
                selected_date,
                (self.map_x_2 + self.btn_w/2, self.map_y_2 - self.btn_h/2+3), True,
            )
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

            if self.no_filedialog:
                graphics.text(
                    screen, rgb.red, self.fontmd,
                    "Zenity or KDialog packages are requied to display file dialog.",
                    (self.screen_x/2, self.bot_y_ui-21),
                )

            # double click counter (not graphics related, but must be outside of input functions)
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
            prop_1 = [int(self.fullscreen), 3, int(self.antial), int(self.vsync), int(self.mouse_warp), int(self.bg_stars_enable)]
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
            prop_4 = [3, int(self.new_color), int(self.cluster_enable), int(self.cluster_new), numba_button, fastmath_button]
            graphics.buttons_vertical(screen, buttons_set_adv, (self.set_x_4, self.top_margin), prop_4)

            # ui
            graphics.buttons_horizontal(screen, buttons_set_ui, (self.set_x_ui, self.bot_y_ui))

            # warnings
            if self.fullscreen and self.selected_res != 0:
                graphics.text(
                    screen, rgb.red, self.fontmd,
                    "Fullscreen mode may not work when in lower resolutions.",
                    (self.screen_x/2, self.bot_y_ui-28), True,
                )
            if self.restart:
                graphics.text(
                    screen, rgb.red, self.fontmd,
                    "Restart is required for changes to take effect.",
                    (self.screen_x/2, self.bot_y_ui-12), True,
                )

            if self.keybinding is True:
                keybinding.main(screen, clock)
                self.keybinding = False

        # about
        elif self.menu == 5:
            graphics.text(
                screen, rgb.white, self.fontbt,
                "Created by: Marko Zivic",
                (self.screen_x/2, self.about_y - self.btn_h*2), True,
            )
            graphics.text(
                screen, rgb.white, self.fontbt,
                f"Version: {version}",
                (self.screen_x/2, self.about_y - self.btn_h), True,
            )
            graphics.buttons_vertical(screen, buttons_about, (self.about_x, self.about_y), [2, 2, 2, 2, None])
            graphics.text(
                screen, rgb.gray0, self.fontmd,
                "Powered by: Python, pygame-ce, NumPy, Numba",
                (self.screen_x/2, self.about_y + self.btn_h*(len(buttons_about)+2)), True,
            )

        graphics.text(screen, rgb.gray1, self.fontmd, "v" + version, (self.screen_x - 50, self.screen_y - 20))


    def main(self, screen, clock, from_game=False):
        """Main loop for menu"""
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
