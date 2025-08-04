import time

import pygame

from volatilespace.graphics import rgb

VERSION = "0.5.2"

FONTTL = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 42)
FONTHD = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 28)
FONTMD = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)


def main_text(screen, color, font, text, pos):
    """Draw main text"""
    text_surf = font.render(text, True, color)
    text_rect = text_surf.get_rect(center=pos)
    screen.blit(text_surf, text_rect)


stage_texts = [
    "Loading menus",
    "Compiling quartic solver",
    "Compiling shared physics",
    "Compiling COI physics",
    "Compiling game physics",
    "Compiling editor physics",
    "Finishing up",
    ]


class Loading:
    """Loading screen class"""
    def __init__(self, screen):
        self.screen = screen
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.loading_pos = (self.screen_x/2, self.screen_y/2 + FONTHD.get_height() + FONTMD.get_height()*1.5)
        self.prev_stages = []
        self.last_stage = ""
        self.last_time = time.time()


    def stage(self, stage):
        """Set loading stage and draw it"""
        stage_time = time.time() - self.last_time
        self.screen.fill("black")
        main_text(self.screen, rgb.white, FONTTL, "Volatile Space",
                  (self.screen_x/2, self.screen_y/2 - FONTTL.get_height()/2))
        main_text(self.screen, rgb.white, FONTHD, "Loading...",
                  (self.screen_x/2, self.screen_y/2 + FONTHD.get_height()/1.5))
        main_text(self.screen, rgb.gray1, FONTMD, "v" + VERSION, (self.screen_x - 25, self.screen_y - 10))

        text = stage_texts[stage]
        main_text(self.screen, rgb.gray, FONTMD, text, self.loading_pos)

        if self.last_stage:
            self.prev_stages.append(f"{self.last_stage}: {round(stage_time, 2)}s")

        for i, prev_text in enumerate(self.prev_stages[::-1]):
            pos = (self.loading_pos[0], self.loading_pos[1]+30*(i+1))
            color = [max(rgb.gray0[0] - rgb.gray0[0]/len(stage_texts)*(i+1), 0)]*3
            main_text(self.screen, color, FONTMD, prev_text, pos)

        self.last_stage = text
        self.last_time = time.time()

        pygame.display.flip()
