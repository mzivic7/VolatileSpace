import pygame
import webbrowser

from volatilespace import fileops
from volatilespace.graphics import rgb
from volatilespace.graphics import graphics
from ast import literal_eval as leval

graphics = graphics.Graphics()

version = "0.1.4"


buttons_main = ["New Game - WIP", "Load Game - WIP", "Multiplayer - WIP", "Map Editor", "Settings", "About", "Quit"]
buttons_set_vid = ["Fullscreen", "Resolution", "Antialiasing", "Vsync", "Mouse wrap", "Background stars"]
buttons_set_aud = ["WIP"]
buttons_set_gam = ["WIP"]
buttons_set_adv = ["Curve points", "Stars antialiasing", "New star color", "Star clusters", "New clusters"]
buttons_set_ui = ["Accept", "Apply", "Cancel", "Load default"]
buttons_about = ["Wiki", "Github", "Itch.io", "Report a bug", "Back"]


class Menu():
    def __init__(self):
        self.state = 1
        self.menu = 0
        self.click = False
        self.reload_settings()
        self.fonttl = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 42)   # title text font
        self.fonthd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 28)   # heading text font
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.rect_w = 250   # button width
        self.rect_w_h = 200   # for horizontal placement
        self.rect_h = self.fontbt.get_height() + 15   # button height from font height
        self.space = 10   # space between buttons
        self.screen_change = False
        self.res_change = False
        self.restart = False   # restart is needed for settings
        graphics.antial = self.antial
        graphics.set_screen()
        self.set_screen()
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        self.main_y = self.screen_y/2 - (len(buttons_main) * self.rect_h + (len(buttons_main)-1) * self.space - self.fonttl.get_height())/2
        self.main_x = self.screen_x/2 - self.rect_w/2
        self.about_y = self.screen_y/2 - (len(buttons_about)+2 * self.rect_h + (len(buttons_about)+1) * self.space)/2
        self.about_x = self.screen_x/2 - self.rect_w/2
        self.settings_section = self.screen_x/4
        self.set_x_1 = self.settings_section/2 - self.rect_w/2
        self.set_x_2 = self.settings_section/2 * 3 - self.rect_w/2
        self.set_x_3 = self.settings_section/2 * 5 - self.rect_w/2
        self.set_x_4 = self.settings_section/2 * 7 - self.rect_w/2
        self.set_x_ui = self.screen_x/2 - (len(buttons_set_ui) * self.rect_w_h + (len(buttons_set_ui)-1) * self.space)/2
        self.set_y_ui = self.screen_y - 50
    
    
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
    
    
    
    ###### --Keys-- ######
    def input_keys(self, e):
        if self.state != 1 and self.state != 0:   # when returning to main menu
            self.state = 1   # update state
        if e.type == pygame.KEYDOWN:   # if any key is pressed:
            if e.key == pygame.K_ESCAPE:  # if "escape" key is pressed
                if self.menu == 0:
                    self.state = 0   # close program
                else:
                    self.menu = 0
    
    
    
    ###### --Mouse-- ######
    def input_mouse(self, e):
        self.mouse = list(pygame.mouse.get_pos())   # get mouse position
        # left mouse button:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:   # is clicked
            self.click = True   # this is to validate that mouse is clicked inside this menu
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:   # is released
            
            
            if self.click is True:
                if self.menu == 0:   # main menu
                    y_pos = self.main_y
                    for num, text in enumerate(buttons_main):
                        if self.main_x <= self.mouse[0]-1 <= self.main_x + self.rect_w and y_pos <= self.mouse[1]-1 <= y_pos + self.rect_h:
                            if num+1 != 1 and num+1 != 2 and num+1 != 3:   # skip new game, load game, multiplayer
                                self.menu = num + 1   # switch to this menu
                                self.click = False   # reset click, to not carry it to next menu
                        y_pos += self.rect_h + self.space   # calculate position for next button
                
                
            if self.menu == 1:   # new game
                pass   # ### WIP ###
            
            
            if self.menu == 2:   # load game
                pass   # ### WIP ###
            
            
            if self.menu == 3:   # multiplayer
                pass   # ### WIP ###
        
        
            if self.menu == 4:   # map editor
                self.state = 2   # ### TODO ###
                self.menu = 0
            
            
            if self.click is True:
                if self.menu == 5:   # settings
                    
                    # graphics
                    x_pos = self.set_x_1
                    y_pos = 100
                    for num, text in enumerate(buttons_set_vid):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.rect_w and y_pos <= self.mouse[1]-1 <= y_pos + self.rect_h:
                            if num == 0:   # fullscreen
                                self.fullscreen = not self.fullscreen
                                self.screen_change = True
                            elif num == 1:   # resolution
                                if x_pos <= self.mouse[0]-1 <= x_pos + 40:   # minus
                                    self.selected_res += 1   # +1 because avail_res is from largest to smallest
                                    if self.selected_res < 0:   # if selected res is negative
                                        self.selected_res = len(self.avail_res) - 1   # return it to min res
                                    self.res_change = True
                                elif x_pos+self.rect_w-40 <= self.mouse[0]-1 <= x_pos + self.rect_w:   # plus
                                    self.selected_res -= 1
                                    if self.selected_res > len(self.avail_res) - 1:   # if selected res is out of range
                                        self.selected_res = 0   # return it to max res
                                    self.res_change = True
                            elif num == 2:   # antialiasing
                                self.antial = not self.antial
                            elif num == 3:   # vsync
                                self.vsync = not self.vsync
                                self.restart = True
                            elif num == 4:   # mouse wrap
                                self.mouse_wrap = not self.mouse_wrap
                            elif num == 5:   # background stars
                                self.bg_stars_enable = not self.bg_stars_enable
                        y_pos += self.rect_h + self.space   # calculate position for next button
                    
                    # advanced
                    x_pos = self.set_x_4
                    y_pos = 100
                    for num, text in enumerate(buttons_set_adv):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.rect_w and y_pos <= self.mouse[1]-1 <= y_pos + self.rect_h:
                            if num == 0:   # curve points
                                if x_pos <= self.mouse[0]-1 <= x_pos + 40:   # minus
                                    self.curve_points -= 25
                                    if self.curve_points < 0:
                                        self.curve_points = 0
                                if x_pos+self.rect_w-40 <= self.mouse[0]-1 <= x_pos + self.rect_w:   # plus
                                    self.curve_points += 25
                            elif num == 1:   # stars antialiasing
                                self.star_aa = not self.star_aa
                            elif num == 2:   # stars new color
                                self.new_color = not self.new_color
                            elif num == 3:   # cluster enable
                                self.cluster_enable = not self.cluster_enable
                            elif num == 4:   # cluster new
                                self.cluster_new = not self.cluster_new
                        y_pos += self.rect_h + self.space
                    
                    # ui
                    x_pos = self.set_x_ui
                    for num, text in enumerate(buttons_set_adv):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.rect_w and self.set_y_ui <= self.mouse[1]-1 <= self.set_y_ui + self.rect_h:
                            if num == 0 or num == 1:   # accept/apply
                                if num == 0:
                                    self.menu = 0
                                fileops.save_settings("graphics", "fullscreen", self.fullscreen)
                                fileops.save_settings("graphics", "resolution", list(self.avail_res[self.selected_res]))
                                fileops.save_settings("graphics", "antialiasing", self.antial)
                                fileops.save_settings("graphics", "vsync", self.vsync)
                                fileops.save_settings("graphics", "mouse_wrap", self.mouse_wrap)
                                fileops.save_settings("background", "stars", self.bg_stars_enable)
                                fileops.save_settings("graphics", "curve_points", self.curve_points)
                                fileops.save_settings("background", "stars_antialiasing", self.star_aa)
                                fileops.save_settings("background", "stars_new_color", self.new_color)
                                fileops.save_settings("background", "cluster_enable", self.cluster_enable)
                                fileops.save_settings("background", "cluster_new", self.cluster_new)
                                
                                # change windowed/fullscreen
                                if self.screen_change is True:
                                    pygame.display.toggle_fullscreen()
                                    self.set_screen()
                                    graphics.set_screen()
                                    self.screen_change = False
                                
                                # change resolutin
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
                                self.restart = False
                                
                            elif num == 3:   # load default
                                fileops.delete_settings()
                                self.restart = True
                        x_pos += self.rect_w_h + self.space
            
            
            if self.click is True:
                if self.menu == 6:   # about
                    y_pos = self.about_y
                    for num, text in enumerate(buttons_about):
                        if self.about_x <= self.mouse[0]-1 <= self.about_x + self.rect_w and y_pos <= self.mouse[1]-1 <= y_pos + self.rect_h:
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
                        y_pos += self.rect_h + self.space   # calculate position for next button
                
            if self.menu == 7:   # quit
                self.state = 0
            
            self.click = False
        
        return self.state
    
    
    
    ###### --Graphics-- ######
    def gui(self, screen, clock):
        screen.fill((0, 0, 0))   # color screen black
        
        # MAIN MENU #
        if self.menu == 0:
            graphics.text(screen, rgb.white, self.fonttl, "Volatile Space", (self.screen_x/2, self.main_y - self.fonttl.get_height()), True)
            graphics.draw_buttons(screen, buttons_main, (self.main_x, self.main_y), (self.rect_w, self.rect_h), self.space, self.mouse, self.click)
        
        
        elif self.menu == 1:   # new game
            pass
        
        elif self.menu == 2:   # load game
            pass
        
        elif self.menu == 3:   # multiplayer
            pass
        
        elif self.menu == 4:   # map editor
            pass
        
        elif self.menu == 5:   # settings
            
            # video
            graphics.text(screen, rgb.white, self.fonthd, "Video", (self.settings_section/2, 40), True)
            buttons_set_vid[1] = str(self.avail_res[self.selected_res]).replace("(", "").replace(")", "").replace(", ", "x")
            prop_1 = [int(self.fullscreen), 3, int(self.antial), int(self.vsync), int(self.mouse_wrap), int(self.bg_stars_enable)]
            graphics.draw_buttons(screen, buttons_set_vid, (self.set_x_1, 100), (self.rect_w, self.rect_h), self.space, self.mouse, self.click, prop_1)
            
            # audio
            graphics.text(screen, rgb.white, self.fonthd, "Audio", (self.settings_section/2 * 3, 40), True)
            prop_2 = [None]
            graphics.draw_buttons(screen, buttons_set_aud, (self.set_x_2, 100), (self.rect_w, self.rect_h), self.space, self.mouse, self.click, prop_2)
            
            # game
            graphics.text(screen, rgb.white, self.fonthd, "Game", (self.settings_section/2 * 5, 40), True)
            prop_3 = [None]
            graphics.draw_buttons(screen, buttons_set_gam, (self.set_x_3, 100), (self.rect_w, self.rect_h), self.space, self.mouse, self.click, prop_3)
            
            # advanced
            graphics.text(screen, rgb.white, self.fonthd, "Advanced", (self.settings_section/2 * 7, 40), True)
            buttons_set_adv[0] = "Curve: " + str(self.curve_points)
            prop_4 = [3, int(self.star_aa), int(self.new_color), int(self.cluster_enable), int(self.cluster_new)]
            graphics.draw_buttons(screen, buttons_set_adv, (self.set_x_4, 100), (self.rect_w, self.rect_h), self.space, self.mouse, self.click, prop_4)
            
            # ui
            graphics.draw_buttons_hor(screen, buttons_set_ui, (self.set_x_ui, self.set_y_ui), (self.rect_w_h, self.rect_h), self.space, self.mouse, self.click)
            
            # warnings
            if self.fullscreen is True and self.selected_res != 0:
                graphics.text(screen, rgb.red, self.fontmd, "Fullscreen mode may not work when in lower resolutions.", (self.screen_x/2, self.set_y_ui-28), True)
            if self.restart is True:
                graphics.text(screen, rgb.red, self.fontmd, "Restart is required for changes to take effect.", (self.screen_x/2, self.set_y_ui-12), True)
        
        elif self.menu == 6:   # about
            graphics.text(screen, rgb.white, self.fontbt, "Created by: Marko Zivic", (self.screen_x/2, self.about_y - self.rect_h*2), True)
            graphics.text(screen, rgb.white, self.fontbt, "Version: " + version, (self.screen_x/2, self.about_y - self.rect_h), True)
            graphics.draw_buttons(screen, buttons_about, (self.about_x, self.about_y), (self.rect_w, self.rect_h), self.space, self.mouse, self.click, [2, 2, 2, 2, None])
        
        
        graphics.text(screen, rgb.gray, self.fontmd, "v" + version, (self.screen_x - 120, self.screen_y - 20))
        graphics.text(screen, rgb.gray, self.fontmd, str(self.mouse), (self.screen_x - 80, self.screen_y - 40))
        graphics.text(screen, rgb.gray, self.fontmd, "fps: " + str(int(clock.get_fps())), (self.screen_x - 60, self.screen_y - 20))
