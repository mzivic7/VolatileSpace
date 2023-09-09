import pygame
from ast import literal_eval as leval


def main():
    ###### --Initiaization-- ######
    update = 60   # screen update frequency
    from volatilespace import fileops
    
    
    ###### --Start pygame-- ######
    pygame.init()
    pygame.display.set_caption('Volatile Space')
    # pygame.display.set_icon(pygame.image.load('img/icon.png'))   # set window icon
    if leval(fileops.load_settings("graphics", "first_run")) is True:   # if this is first time running
        avail_res = pygame.display.get_desktop_sizes()   # available resolutions
        (screen_x, screen_y) = avail_res[0]   # use highest resolution
        fileops.save_settings("graphics", "resolution", [screen_x, screen_y])   # write resolution to settings file
        fileops.save_settings("graphics", "first_run", False)
    else:
        (screen_x, screen_y) = fileops.load_settings("graphics", "resolution")
    fullscreen = leval(fileops.load_settings("graphics", "fullscreen"))   # load screen mode setting
    vsync = leval(fileops.load_settings("graphics", "vsync"))
    if fullscreen is True:
        screen = pygame.display.set_mode((screen_x, screen_y), pygame.FULLSCREEN, vsync=vsync)   # set window size and fullscreen
    else:
        screen = pygame.display.set_mode((screen_x, screen_y), vsync=vsync)   # set window size and windowed
    clock = pygame.time.Clock()   # start clock
    pygame.time.set_timer(pygame.USEREVENT, int(round(1000/60)))   # userevent is called every 1/60 of second (rounded to 17ms)


    ###### --Load classes-- ######
    from volatilespace import menu
    from volatilespace import game
    from volatilespace import editor
    menu = menu.Menu()
    editor = editor.Editor()
    game = game.Game()


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
            
            
            if e.type == pygame.QUIT:
                run = False   # if quit, break loop
        
        
        ###### --Graphics-- ######
        editor.graphics(screen, clock)
        
        
        pygame.display.flip()   # update screen
        clock.tick(update)   # screen update frequency

    pygame.quit()   # quit gently



if __name__ == "__main__":
    main()
