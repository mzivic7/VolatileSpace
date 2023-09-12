import pygame

from volatilespace import fileops
from volatilespace.graphics import rgb
from volatilespace.graphics import graphics
from ast import literal_eval as leval

graphics = graphics.Graphics()

version = "0.1.3"


class Menu():
    def __init__(self):
        self.state = 1
        self.scroll = 0
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
        self.fonttl = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 32)   # title text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.fontsm = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 10)   # small text font
        graphics.antial = self.antial
        graphics.set_screen()
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
    
    
    
    ###### --Keys-- ######
    def input_keys(self, e):
        if self.state != 1 and self.state != 0:   # when returning to main menu
            self.state = 1   # update state
        if e.type == pygame.KEYDOWN:   # if any key is pressed:
            if e.key == pygame.K_ESCAPE:  # if "escape" key is pressed
                self.state = 0   # close program
    
    
    
    ###### --Mouse-- ######
    def input_mouse(self, e):
        self.mouse = list(pygame.mouse.get_pos())   # get mouse position
        # left mouse button:
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:   # is clicked
            self.click = True   # this is to validate that mouse is clicked inside this menu
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:   # is released
            if self.click is True:
                self.state = 2
                self.click = False
        
        return self.state
        
        # mouse wheel
        if e.type == pygame.MOUSEWHEEL:
            self.scroll += e.y
            pass
    
    
    
    ###### --Menus-- ######
    def gui(self, screen, clock):
        screen.fill((0, 0, 0))   # color screen black
        
        graphics.text(screen, rgb.white, self.fonttl, "MAIN MENU", (self.screen_x/2, self.screen_y/2 - 20), True)
        graphics.text(screen, rgb.white, self.fontmd, "Click to start game", (self.screen_x/2, self.screen_y/2 + 20), True)
        graphics.text(screen, rgb.white, self.fontmd, "Escape to quit", (self.screen_x/2, self.screen_y/2 + 40), True)
