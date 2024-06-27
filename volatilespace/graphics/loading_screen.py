import pygame
from volatilespace.graphics import rgb
import time

version = "0.5.2"

fonttl = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 42)
fonthd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 28)
fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)


def main_text(screen, color, font, text, pos):
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=pos)
    screen.blit(text_surf, text_rect)


class Loading:
    def __init__(self, screen):
        self.screen = screen
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.loading_pos = (self.screen_x/2, self.screen_y/2 + fonthd.get_height() + fontmd.get_height()*1.5)
        self.prev_stages = []
        self.last_stage = ""
        self.last_time = time.time()


    def stage(self, stage):
        stage_time = time.time() - self.last_time
        self.screen.fill("black")
        main_text(self.screen, rgb.white, fonttl, "Volatile Space",
                  (self.screen_x/2, self.screen_y/2 - fonttl.get_height()/2))
        main_text(self.screen, rgb.white, fonthd, "Loading...",
                  (self.screen_x/2, self.screen_y/2 + fonthd.get_height()/1.5))
        main_text(self.screen, rgb.gray1, fontmd, "v" + version, (self.screen_x - 25, self.screen_y - 10))
        match stage:
            case 1:
                text = "Loading menus"
            case 2:
                text = "Compiling shared physics"
            case 3:
                text = "Compiling COI physics"
            case 4:
                text = "Compiling game physics"
            case 5:
                text = "Compiling editor physics"
            case 6:
                text = "Finishing up"
        main_text(self.screen, rgb.gray, fontmd, text, self.loading_pos)

        if self.last_stage:
            self.prev_stages.append(f"{self.last_stage}: {round(stage_time, 2)}s")

        for i, prev_text in enumerate(self.prev_stages[::-1]):
            pos = (self.loading_pos[0], self.loading_pos[1]+30*(i+1))
            color = [max(rgb.gray0[0] - 25*(i+1), 0)]*3
            main_text(self.screen, color, fontmd, prev_text, pos)

        self.last_stage = text
        self.last_time = time.time()

        pygame.display.flip()
