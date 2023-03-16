import pygame

import numpy as np
import math
import datetime
from configparser import ConfigParser
import random

from volatilespace.graphics import rgb
#from volatilespace import menu
#from volatilespace import game
from volatilespace import editor
from volatilespace import fileops
from volatilespace import physics_engine


###### --Initial variables-- ######
update = 60   # screen update frequency


###### --Initialize GUI-- ######
pygame.init()   # initialize pygame
pygame.display.set_caption('Volatile Space')
#pygame.display.set_icon(pygame.image.load('img/icon.png'))   # set window icon
infoObject = pygame.display.Info()
screen_x, screen_y = infoObject.current_w, infoObject.current_h   # window width, window height
screen = pygame.display.set_mode((infoObject.current_w, infoObject.current_h))   # set window size
clock = pygame.time.Clock()   # start clock
pygame.time.set_timer(pygame.USEREVENT, int(round(1000/60)))   # userevent is called every 1/60 of second (rounded to 17ms)


###### --Load classes-- ######
physics = physics_engine.Physics()
editor = editor.Editor()


###### --Load initial bodies-- ######
editor.load_system()


###### --Main loop-- ######
run = True
while run:
    for e in pygame.event.get():
        
        
        ###### --Keys-- ######
        run = editor.input_keys(e)
        
        
        ###### --Mouse-- ######
        editor.input_mouse(e)
        
        
        ###### --Calculations-- ######
        editor.physics(e)
    
    
    if e.type == pygame.QUIT: run = False   # if quit, break loop
    
    
    ###### --Graphics-- ######
    editor.graphics(screen, clock)
    
    
    pygame.display.flip()   # update screen
    clock.tick(update)   # screen update frequency

pygame.quit()   # quit gently
