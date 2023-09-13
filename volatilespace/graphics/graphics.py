import pygame
import math
from pygame import gfxdraw

from volatilespace import fileops
from volatilespace.graphics import rgb


class Graphics():
    def __init__(self):
        self.antial = True
        self.grid_mode_txts = ["Default", "Selected body", "Orbited body"]   # text displayed on screen
        self.grid_mode = 0   # grid mode: 0 - global, 1 - selected body, 2 - parent
        self.grid_mode_prev = 0   # history of grid mode
        self.screen_x, self.screen_y = 0, 0   # initial window width, window height
        self.timed_text_enable = False   # for drawing timed text on screen
        self.timer = 0   # timer for drawing timed text on screen
        self.spacing_min = int(fileops.load_settings("graphics", "grid_spacing_min"))   # minimum and maximum size spacing of grid
        self.spacing_max = int(fileops.load_settings("graphics", "grid_spacing_max"))
        self.color, self.font, self.text_str, self.pos, self.time, self.center = (0, 0, 0), 0, 0, [0, 0], 0, 0   # initial vars for timed text
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.fontsm = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 10)   # small text font
        self.link = pygame.image.load("img/link.png")
        
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        
    
    def draw_line(self, surface, color, point_1, point_2, thickness):
        """Draw a straight line"""
        if self.antial is True:
            pygame.draw.aaline(surface, color, point_1, point_2)
        else:
            pygame.draw.line(surface, color, point_1, point_2, thickness)

    
    def draw_lines(self, surface, colors, points, thickness, closed=False):
        """Draw multiple contiguous straight line segments"""
        if self.antial is True:
            pygame.draw.aalines(surface, colors, closed, points)
        else:
            pygame.draw.lines(surface, colors, closed, points, thickness)

    
    def draw_circle(self, surface, color, center, radius, thickness):
        """Draw a circle"""
        if radius < 60000:   # no need to draw so large circle lines
            if self.antial is True and radius < 1000:   # limit radius because of gfxdraw bug ### BUG ### 32767
                # if circle is off screen dont draw it, because gfxdraw uses short integers for position and radius
                if center[0]+radius > 0 and center[0]-radius < self.screen_x and center[1]+radius > 0 and center[1]-radius < self.screen_y:
                    gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius), color)   # draw initial circle ### BUG ###
                    if thickness != 1:   # antialiased line has no thickness option ### BUG ###
                        for num in range(1, thickness):   # draw one more circle for each number of thickness
                            gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius)+num, color)
            else:
                pygame.draw.circle(surface, color, center, radius, thickness)
        
    
    def draw_circle_fill(self, surface, color, center, radius, antial=None):
        """Draw a filled circle"""
        if antial is None:
            func_antial = self.antial
        else:
            func_antial = antial   # antial as function argument is optional override to global antial
        if radius == 1:   # if star radius is 1px
            gfxdraw.pixel(surface, int(center[0]), int(center[1]), color)    # draw just that pixel
        else:   # if radius is more than 1px (radius-1 because 1px radius covers 4px total)
            if func_antial is True and radius < 1000:   # ### BUG ### 32767
                if center[0] + radius > 0 and center[0] - radius < self.screen_x:
                    gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius - 1), color)
                    gfxdraw.filled_circle(surface, int(center[0]), int(center[1]), int(radius - 1), color)
            else:
                pygame.draw.circle(surface, color, center, radius - 1)
    
    
    def text(self, screen, color, font, text, pos, center=False, bg_color=False):   # center text rectangle to point
        """Display text on screen, optionnally centered to given coordinates"""
        if center is True:
            text = font.render(text, True, color)   # render text font
            text_rect = text.get_rect(center=(pos[0], pos[1]))   # position text rectangle - center
            if bg_color is not False:
                pygame.draw.rect(screen, bg_color, text_rect)
            screen.blit(text, text_rect)   # blit to screen
        else:
            if bg_color is not False:   # if there is background rectangle
                text = font.render(text, True, color)   # render text font
                text_rect = text.get_rect(topleft=(pos[0], pos[1]))   # position text rectangle - top left
                pygame.draw.rect(screen, bg_color, text_rect)   # draw background rectangle
                screen.blit(text, text_rect)   # blit text
            else:
                screen.blit(font.render(text, True, color), pos)
    
    
    def timed_text_init(self, color, font, text, pos, time=2, center=False, bg_color=False):
        """Timed text on screen, optionally centered to given coordinates, this is activated once"""
        self.timed_text_enable = True
        self.color, self.font, self.text_str, self.pos, self.time, self.center = color, font, text, pos, time, center
    
    
    def timed_text(self, screen, clock):
        """Print timed text on screen"""
        if self.timed_text_enable is True:   # if timed text is activated
            time_s = self.time * clock.get_fps()   # time from second into frames
            self.text(screen, self.color, self.font, self.text_str, self.pos, self.center)
            if self.timer > time_s:   # timer that disables timed text after specified time
                self.timed_text_enable = False
                self.timer = 0
            self.timer += 1
    
    
    def draw_grid(self, screen, grid_mode, origin, zoom):
        """Draw grid of lines expanding from origin"""
        self.grid_mode = grid_mode
        spacing = 10 * zoom   # initial spacing
        while spacing < self.spacing_min:   # if spacing gets smaller than limit
            spacing *= 2   # double increase spacing
        while spacing > self.spacing_min:   # if spacinggets larger than limit
            spacing /= 2.  # double decrease spacing
        line_num_x = math.ceil(self.screen_x / spacing)   # number of vertical lines on screen
        line_num_y = math.ceil(self.screen_y / spacing)   # horizontal
        grid_mode_txt = self.grid_mode_txts[grid_mode]   # get current grid mode text
        if self.grid_mode_prev != self.grid_mode:   # if grid mode has changed, print message on screen
            self.timed_text_init(rgb.gray, self.fontmd, "Grid mode: " + grid_mode_txt, (self.screen_x/2, 70), 1.5, True)
        self.grid_mode_prev = self.grid_mode   # update grid mode history
        
        for line in range(line_num_x):   # for each vertical line
            pos_x = origin[0] + (spacing * line)   # calculate its position from origin line
            moved = 0   # how much have line index moved
            while pos_x > self.screen_x:   # as long line is off screen - right
                pos_x -= spacing * line_num_x   # move it left
                moved -= line_num_x   # moving line index left
            while pos_x < 0:   # if line is off screen - left
                pos_x += spacing * line_num_x   # move it right
                moved += line_num_x   # moving line index right
            if line == 0 and moved == 0:   # at origin
                self.draw_line(screen, rgb.red2, (pos_x, 0), (pos_x, self.screen_y), 2)   # red line
                self.text(screen, rgb.red2, self.fontsm, "0", (pos_x, self.screen_y - 10), True, rgb.black)
            elif abs(line + moved) % 5 == 0:   # every fifth line, but include line index movement
                self.draw_line(screen, rgb.gray1, (pos_x, 0), (pos_x, self.screen_y), 1)   # gray line
                sim_pos_x = round(((line + moved) * spacing) / zoom)   # calculate simulaion coordinate
                self.text(screen, rgb.gray1, self.fontsm, str(sim_pos_x), (pos_x, self.screen_y - 10), True, rgb.black)
            else:   # every other line
                sim_pos_x = round(((line + moved) * spacing) / zoom)
                self.draw_line(screen, rgb.gray2, (pos_x, 0), (pos_x, self.screen_y), 1)   # dark gray line
                self.text(screen, rgb.gray2, self.fontsm, str(sim_pos_x), (pos_x, self.screen_y - 10), True, rgb.black)
        
        for line in range(line_num_y):   # for each horizontal line
            pos_y = origin[1] + (spacing * line)
            moved = 0
            while pos_y > self.screen_y:
                pos_y -= spacing * line_num_y
                moved -= line_num_y
            while pos_y < 0:
                pos_y += spacing * line_num_y
                moved += line_num_y
            if line == 0 and moved == 0:
                self.draw_line(screen, rgb.red2, (0, pos_y), (self.screen_x, pos_y), 2)
                self.text(screen, rgb.red2, self.fontsm, "0", (10, pos_y-5), False, rgb.black)
            elif abs(line + moved) % 5 == 0:
                self.draw_line(screen, rgb.gray1, (0, pos_y), (self.screen_x, pos_y), 1)
                sim_pos_y = round(-((line + moved) * spacing) / zoom)
                self.text(screen, rgb.gray1, self.fontsm, str(sim_pos_y), (5, pos_y-5), False, rgb.black)
            else:   # every other line
                self.draw_line(screen, rgb.gray2, (0, pos_y), (self.screen_x, pos_y), 1)
                sim_pos_y = round(-((line + moved) * spacing) / zoom)
                self.text(screen, rgb.gray2, self.fontsm, str(sim_pos_y), (5, pos_y-5), False, rgb.black)
        
        
    def draw_buttons(self, screen, buttons_txt, pos, size, space, mouse, click, prop=None):
        """Draws buttons with mouse over and click effect. 
        Properties are passed as list with value for each button. 
        Values can be: None - no effect, 0 - red color (OFF), 1 - green color (ON), 2 - add link icon on button"""
        x, y = pos[0], pos[1]
        w, h = size[0], size[1]
        for num, text in enumerate(buttons_txt):
            color = rgb.black
            if "WIP" not in text:   # black out WIP buttons
                if prop is not None and prop[num] == 0:   # depending on properties value, determine color
                    color = rgb.red_s1
                elif prop is not None and prop[num] == 1:
                    color = rgb.green_s1
                else:
                    color = rgb.gray3
                    
            # mouse over button
            if x <= mouse[0]-1 <= x + w and y <= mouse[1]-1 <= y + h:
                if "WIP" not in text:
                    if prop is not None and prop[num] == 0:
                        color = rgb.red_s2
                    elif prop is not None and prop[num] == 1:
                        color = rgb.green_s2
                    else:
                        color = rgb.gray2
                    
                # click on button
                if click is True:
                    if "WIP" not in text:
                        if prop is not None and prop[num] == 0:
                            color = rgb.red_s3
                        elif prop is not None and prop[num] == 1:
                            color = rgb.green_s3
                        else:
                            color = rgb.gray1
                            
            pygame.draw.rect(screen, color, (x, y, w, h))
            pygame.draw.rect(screen, rgb.white, (x, y, w, h), 1)
            # button text
            self.text(screen, rgb.white, self.fontbt, text, (x + w/2, y + h/2), True)
            if prop is not None and prop[num] == 2:   # from properties value add link icon
                screen.blit(self.link, (x+w-40, y))
            y += h + space   # calculate position for next button
