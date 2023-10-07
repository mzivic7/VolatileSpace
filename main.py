import pygame
from ast import literal_eval as leval

from volatilespace import fileops


def main():
    ###### --Start pygame-- ######
    pygame.init()
    pygame.display.set_caption('Volatile Space')
    pygame.display.set_icon(pygame.image.load('img/icon.png'))   # set window icon
    if leval(fileops.load_settings("graphics", "first_run")) is True:   # if this is first time running
        avail_res = pygame.display.get_desktop_sizes()   # available resolutions
        (screen_x, screen_y) = avail_res[0]   # use highest resolution
        fileops.save_settings("graphics", "resolution", [screen_x, screen_y])   # write resolution to settings file
        fileops.save_settings("graphics", "first_run", False)
    else:
        (screen_x, screen_y) = fileops.load_settings("graphics", "resolution")
    fullscreen = leval(fileops.load_settings("graphics", "fullscreen"))   # load screen mode setting
    vsync = leval(fileops.load_settings("graphics", "vsync"))
    if fullscreen is True:   # set window size and fullscreen
        screen = pygame.display.set_mode((screen_x, screen_y), pygame.FULLSCREEN, vsync=vsync)
    else:
        screen = pygame.display.set_mode((screen_x, screen_y), vsync=vsync)
    clock = pygame.time.Clock()   # start clock
    pygame.time.set_timer(pygame.USEREVENT, int(round(1000/60)))   # userevent is called every 1/60 of second (rounded to 17ms)


    ###### --Load classes-- ######
    from volatilespace import menu
    from volatilespace import game
    from volatilespace import editor
    menu = menu.Menu()
    editor = editor.Editor()
    game = game.Game()


    ###### --Main loop-- ######
    state = 1   # enter main menu on startup
    run = True
    while run:
        for e in pygame.event.get():
            if state == 1:   # main menu
                state = menu.main(screen, clock)
                if state == 2:
                    editor.reload_settings()
                    selected_path = menu.selected_path
                    if selected_path is not None:
                        try:   # check if file exists
                            with open(selected_path) as f:
                                text = f.read()
                        except Exception:
                            state = 1
                            menu.gen_map_list()
                        if state == 2:
                            editor.load_system(selected_path)
            elif state == 2:   # editor
                state = editor.main(screen, clock)
            elif state == 3:   # game
                pass
            elif state == 4:   # settings from game/editor
                state = menu.main(screen, clock, True)
                if state == 2:
                    editor.reload_settings()
            elif state == 0:   # quit
                run = False
            
            if e.type == pygame.QUIT:
                run = False   # if quit, break loop
    
    pygame.quit()   # quit gently



if __name__ == "__main__":
    main()
