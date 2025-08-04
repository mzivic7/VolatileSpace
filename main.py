from ast import literal_eval

import pygame
from numba import njit  # noqa

from volatilespace import peripherals


# these functions are used to import physics which is then compiled
# but pygame is kept responsive, and able to quit
def import_quartic_solver():
    """Import just to compile numba"""
    from volatilespace.physics import quartic_solver   # noqa


def import_phys_shared():
    """Import just to compile numba"""
    from volatilespace.physics import phys_shared   # noqa
    from volatilespace.physics.enhanced_kepler_solver import solve_kepler_ell   # noqa


def import_orbit_intersect():
    """Import just to compile numba"""
    from volatilespace.physics import orbit_intersect   # noqa


def import_game():
    """Import just to compile numba"""
    from volatilespace import game   # noqa


def import_editor():
    """Import just to compile numba"""
    from volatilespace import editor   # noqa


def main():
    """Main function"""
    # pygame.mixer.pre_init(buffer=2048)
    # pygame.init()   # not using to not start mixer at all
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Volatile Space")
    pygame.display.set_icon(pygame.image.load("img/icon.png"))
    if literal_eval(peripherals.load_settings("graphics", "first_run")) is True:
        avail_res = pygame.display.get_desktop_sizes()
        (screen_x, screen_y) = avail_res[0]   # use highest resolution
        peripherals.save_settings("graphics", "resolution", [screen_x, screen_y])
        peripherals.save_settings("graphics", "first_run", False)
    else:
        (screen_x, screen_y) = peripherals.load_settings("graphics", "resolution")
    fullscreen = literal_eval(peripherals.load_settings("graphics", "fullscreen"))
    vsync = literal_eval(peripherals.load_settings("graphics", "vsync"))
    if fullscreen is True:
        screen = pygame.display.set_mode((screen_x, screen_y), pygame.FULLSCREEN, vsync=vsync)
    else:
        screen = pygame.display.set_mode((screen_x, screen_y), vsync=vsync)
    clock = pygame.time.Clock()
    # userevent is called every 1/60 of second (rounded to 17ms)
    pygame.time.set_timer(pygame.USEREVENT, int(round(1000/60)))


    from volatilespace.graphics import loading_screen
    from volatilespace.utils import responsive_blocking
    loading = loading_screen.Loading(screen)
    loading.stage(0)
    from volatilespace import menu
    loading.stage(1)
    responsive_blocking(target=import_quartic_solver)
    loading.stage(2)
    responsive_blocking(target=import_phys_shared)
    loading.stage(3)
    responsive_blocking(target=import_orbit_intersect)
    loading.stage(4)
    responsive_blocking(target=import_game)
    from volatilespace import game
    loading.stage(5)
    responsive_blocking(target=import_editor)
    from volatilespace import editor
    loading.stage(6)
    menu = menu.Menu()
    game = game.Game()
    editor = editor.Editor()


    state = 1   # enter main menu on startup
    run = True
    while run:
        for event in pygame.event.get():
            if state == 0:   # quit
                run = False
            elif state == 1:   # main menu
                state = menu.main(screen, clock)
                if state == 2:
                    editor.reload_settings()
                    selected_path = menu.selected_path
                    if selected_path is not None:
                        try:   # check if file exists
                            with open(selected_path) as f:
                                _ = f.read()
                        except Exception:
                            state = 1
                            menu.gen_map_list()
                        if state == 2:
                            editor.load_system(selected_path)
                elif state == 3:   # game
                    game.reload_settings()
                    selected_path = menu.selected_path
                    if selected_path is not None:
                        try:   # check if file exists
                            with open(selected_path) as f:
                                _ = f.read()
                        except Exception:
                            state = 1
                            menu.gen_map_list()
                        if state == 3:
                            game.load_system(selected_path)
            elif state == 2:   # editor
                state = editor.main(screen, clock)
            elif state == 3:   # game
                state = game.main(screen, clock)
            elif state >= 10:   # settings from game/editor
                _ = menu.main(screen, clock, True)
                state = int(str(state)[1])
                if state == 2:
                    editor.reload_settings()
                elif state == 3:
                    game.reload_settings()
            if event.type == pygame.QUIT:
                run = False
    pygame.quit()


if __name__ == "__main__":
    main()
