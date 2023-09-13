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
buttons_about = ["Wiki", "Github", "Itch.io", "Report a bug", "Back"]


class Menu():
    def __init__(self):
        self.state = 1
        self.menu = 0
        self.click = False
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
        self.antial = leval(fileops.load_settings("graphics", "antialiasing"))   # global antialiasing
        self.fonttl = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 42)   # title text font
        self.fonthd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 28)   # heading text font
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.rect_num = len(buttons_main)
        self.rect_w_0 = 250   # find largest text box and make all buttons that large   ### TODO ###
        self.rect_h = self.fontbt.get_height() + 15   # button height from font height
        self.space = 10   # space between buttons
        graphics.antial = self.antial
        graphics.set_screen()
        self.set_screen()
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        self.main_y = self.screen_y/2 - (self.rect_num * self.rect_h + (self.rect_num-1) * self.space - self.fonttl.get_height())/2
        self.main_x = self.screen_x/2 - self.rect_w_0/2
        self.about_y = self.screen_y/2 - (self.rect_num+2 * self.rect_h + (self.rect_num+1) * self.space)/2
        self.about_x = self.screen_x/2 - self.rect_w_0/2
        self.settings_section = self.screen_x/4
        self.set_x_1 = self.settings_section/2 - self.rect_w_0/2
        self.set_x_2 = self.settings_section/2 * 3 - self.rect_w_0/2
        self.set_x_3 = self.settings_section/2 * 5 - self.rect_w_0/2
        self.set_x_4 = self.settings_section/2 * 7 - self.rect_w_0/2
    
    
    
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
                        if self.main_x <= self.mouse[0]-1 <= self.main_x + self.rect_w_0 and y_pos <= self.mouse[1]-1 <= y_pos + self.rect_h:
                            if num+1 != 1 and num+1 != 2 and num+1 != 3:   # skip new game, load game, multiplayer
                                self.menu = num + 1   # switch to this menu
                                self.click = False   # reset click to not carry it to next menu
                        y_pos += self.rect_h + self.space   # calculate position for next button
                
            if self.menu == 1:   # new game
                pass   # WIP #
            
            if self.menu == 2:   # load game
                pass   # WIP #
            
            if self.menu == 3:   # multiplayer
                pass   # WIP #
        
            if self.menu == 4:   # map editor
                self.state = 2   # WIP #
                self.menu = 0
            
            if self.menu == 5:   # settings
                pass   # WIP #
            
            if self.click is True:
                if self.menu == 6:   # about
                    y_pos = self.about_y
                    for num, text in enumerate(buttons_about):
                        if self.about_x <= self.mouse[0]-1 <= self.about_x + self.rect_w_0 and y_pos <= self.mouse[1]-1 <= y_pos + self.rect_h:
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
    
    
    
    ###### --Menus-- ######
    def gui(self, screen, clock):
        screen.fill((0, 0, 0))   # color screen black
        
        # MAIN MENU #
        if self.menu == 0:
            graphics.text(screen, rgb.white, self.fonttl, "Volatile Space", (self.screen_x/2, self.main_y - self.fonttl.get_height()), True)
            graphics.draw_buttons(screen, buttons_main, (self.main_x, self.main_y), (self.rect_w_0, self.rect_h), self.space, self.mouse, self.click)
        
        
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
            prop_1 = [1, None, 1, 0, 1, 0]
            graphics.draw_buttons(screen, buttons_set_vid, (self.set_x_1, 100), (self.rect_w_0, self.rect_h), self.space, self.mouse, self.click, prop_1)
            
            # audio
            graphics.text(screen, rgb.white, self.fonthd, "Audio", (self.settings_section/2 * 3, 40), True)
            prop_2 = [None]
            graphics.draw_buttons(screen, buttons_set_aud, (self.set_x_2, 100), (self.rect_w_0, self.rect_h), self.space, self.mouse, self.click, prop_2)
            
            # game
            graphics.text(screen, rgb.white, self.fonthd, "Game", (self.settings_section/2 * 5, 40), True)
            prop_3 = [None]
            graphics.draw_buttons(screen, buttons_set_gam, (self.set_x_3, 100), (self.rect_w_0, self.rect_h), self.space, self.mouse, self.click, prop_3)
            
            # advanced
            graphics.text(screen, rgb.white, self.fonthd, "Advanced", (self.settings_section/2 * 7, 40), True)
            prop_4 = [None, 1, 0, 1, 0]
            graphics.draw_buttons(screen, buttons_set_adv, (self.set_x_4, 100), (self.rect_w_0, self.rect_h), self.space, self.mouse, self.click, prop_4)
        
        elif self.menu == 6:   # about
            graphics.text(screen, rgb.white, self.fontbt, "Created by: Marko Zivic", (self.screen_x/2, self.about_y - self.rect_h*2), True)
            graphics.text(screen, rgb.white, self.fontbt, "Version: " + version, (self.screen_x/2, self.about_y - self.rect_h), True)
            graphics.draw_buttons(screen, buttons_about, (self.about_x, self.about_y), (self.rect_w_0, self.rect_h), self.space, self.mouse, self.click, [2, 2, 2, 2, None])
        
        
        graphics.text(screen, rgb.gray, self.fontmd, "v" + version, (self.screen_x - 120, self.screen_y - 20))
        graphics.text(screen, rgb.gray, self.fontmd, str(self.mouse), (self.screen_x - 80, self.screen_y - 40))
        graphics.text(screen, rgb.gray, self.fontmd, "fps: " + str(int(clock.get_fps())), (self.screen_x - 60, self.screen_y - 20))
