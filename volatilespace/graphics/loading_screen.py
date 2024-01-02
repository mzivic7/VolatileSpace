import pygame

version = "0.5.1"

from volatilespace.graphics import rgb

fonttl = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 42)
fonthd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 28)
fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)

def text(screen, color, font, text, pos):
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=pos)
    screen.blit(text_surf, text_rect)

def loading(screen, stage):
    screen.fill("black")
    screen_x, screen_y = pygame.display.get_surface().get_size()
    text(screen, rgb.white, fonttl, "Volatile Space",
              (screen_x/2, screen_y/2 - fonttl.get_height()/2))
    text(screen, rgb.white, fonthd, "Loading...",
              (screen_x/2, screen_y/2 + fonthd.get_height()/1.5))
    pos = (screen_x/2, screen_y/2 + fonthd.get_height() + fontmd.get_height()*1.5)
    match stage:
        case 1:
            text(screen, rgb.gray, fontmd, "Loading menus", pos)
        case 2:
            text(screen, rgb.gray, fontmd, "Compiling game physics", pos)
        case 3:
            text(screen, rgb.gray, fontmd, "Compiling editor physics", pos)
        case 4:
            text(screen, rgb.gray, fontmd, "Finishing up", pos)
    text(screen, rgb.gray1, fontmd, "v" + version, (screen_x - 25, screen_y - 10))
    pygame.display.flip()
