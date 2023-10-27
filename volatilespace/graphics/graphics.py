import pygame
import math
from pygame import gfxdraw   # gfxdraw ### DEPRECATED ###
from ast import literal_eval as leval

from volatilespace import fileops
from volatilespace.graphics import rgb

grid_mode_txts = ["Default", "Selected body", "Orbited body"]   # text displayed on screen


class Graphics():
    def __init__(self):
        self.grid_mode = 0   # grid mode: 0 - global, 1 - selected body, 2 - parent
        self.grid_mode_prev = 0   # history of grid mode
        self.screen_x, self.screen_y = 0, 0   # initial window width, window height
        self.timed_text_enable = False   # for drawing timed text on screen
        self.timer = 0   # timer for drawing timed text on screen
        self.reload_settings()
        self.color, self.font, self.text_str, self.pos, self.time, self.center = (0, 0, 0), 0, 0, [0, 0], 0, 0   # initial vars for timed text
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.fontsm = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 10)   # small text font
        self.link = pygame.image.load("img/link.png")
        self.plus = pygame.image.load("img/plus.png")
        self.minus = pygame.image.load("img/minus.png")
        
        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.txt_y_margin = 8  # empty space between text and button edge
        self.btn_h = self.fontbt.get_height() + self.txt_y_margin * 2   # button height from font height
        self.btn_s = 36   # small square button
        self.space = 10
        self.click = False
        self.mouse = [0, 0]
        self.disable_buttons = False
        
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        
    
    def reload_settings(self):
        self.antial = leval(fileops.load_settings("graphics", "antialiasing"))
        self.spacing_min = int(fileops.load_settings("graphics", "grid_spacing_min"))   # minimum and maximum size spacing of grid
        self.spacing_max = int(fileops.load_settings("graphics", "grid_spacing_max"))
        
    
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

    
    def draw_circle(self, surface, color, center, radius, thickness):   # gfxdraw ### DEPRECATED ###
        """Draw a circle"""
        if radius < 60000:   # no need to draw so large circle lines
            if self.antial is True and radius < 1000:   # limit radius because of gfxdraw bug
                # if circle is off screen dont draw it, because gfxdraw uses short integers for position and radius
                if center[0]+radius > 0 and center[0]-radius < self.screen_x and center[1]+radius > 0 and center[1]-radius < self.screen_y:
                    gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius), color)   # draw initial circle
                    if thickness != 1:   # antialiased line has no thickness option
                        for num in range(1, thickness):   # draw one more circle for each number of thickness
                            gfxdraw.aacircle(surface, int(center[0]), int(center[1]), int(radius)+num, color)
            else:
                pygame.draw.circle(surface, color, center, radius, thickness)
        
    
    def draw_circle_fill(self, surface, color, center, radius, antial=None):   # gfxdraw ### DEPRECATED ###
        """Draw a filled circle"""
        if antial is None:
            func_antial = self.antial
        else:
            func_antial = antial   # antial as function argument is optional override to global antial
        if radius == 1:   # if star radius is 1px
            gfxdraw.pixel(surface, int(center[0]), int(center[1]), color)    # draw just that pixel
        else:   # if radius is more than 1px (radius-1 because 1px radius covers 4px total)
            if func_antial is True and radius < 1000:
                if center[0]+radius > 0 and center[0]-radius < self.screen_x and center[1]+radius > 0 and center[1]-radius < self.screen_y:
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
    
    
    def limit_text(self, text, font, width):
        """Limits text length to defined pixel width, adds "..." at end."""
        text_rect = font.render(text, True, rgb.white).get_rect(topleft=(0, 0))
        if text_rect[2] > width - 10:
            while text_rect[2] > width - 10:
                text = text[:-1]
                text_rect = font.render(text, True, rgb.white).get_rect(topleft=(0, 0))
            text = text[:-3] + "..."
        return text
    
    
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
        grid_mode_txt = grid_mode_txts[grid_mode]   # get current grid mode text
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
                self.text(screen, rgb.red2, self.fontsm, "0", (10+self.btn_s, pos_y-5), False, rgb.black)
            elif abs(line + moved) % 5 == 0:
                self.draw_line(screen, rgb.gray1, (0, pos_y), (self.screen_x, pos_y), 1)
                sim_pos_y = round(-((line + moved) * spacing) / zoom)
                self.text(screen, rgb.gray1, self.fontsm, str(sim_pos_y), (5+self.btn_s, pos_y-5), False, rgb.black)
            else:   # every other line
                self.draw_line(screen, rgb.gray2, (0, pos_y), (self.screen_x, pos_y), 1)
                sim_pos_y = round(-((line + moved) * spacing) / zoom)
                self.text(screen, rgb.gray2, self.fontsm, str(sim_pos_y), (5+self.btn_s, pos_y-5), False, rgb.black)
        
        
    def update_mouse(self, mouse, click, disable):
        """Updates dynamically changing values"""
        self.mouse, self.click, self.disable_buttons = mouse, click, disable
        
        
    def buttons_vertical(self, screen, buttons_txt, pos, prop=None, safe=False):
        """Draws buttons with mouseover and self.click effect.
        Properties are passed as list with value for each button.
        Values can be: None - no effect, 0 - red color (OFF), 1 - green color (ON),
        2 - add link icon on button, 3 - +/- buttons, 4 - highlighted, 5 - disabled"""
        (x, y) = pos
        disable_buttons = False
        if safe is False:
            disable_buttons = self.disable_buttons
        for num, text in enumerate(buttons_txt):
            if prop is not None and prop[num] == 5:   # black out disabled buttons
                color = rgb.black
                color_text = rgb.gray
            else:
                color_l = color_r = rgb.gray3
                color_text = rgb.white
                if prop is not None and prop[num] == 0:   # depending on properties value, determine color
                    color = rgb.red_s1
                elif prop is not None and prop[num] == 1:
                    color = rgb.green_s1
                else:
                    color = rgb.gray3
                    
                # mouse over button
                if x <= self.mouse[0]-1 <= x + self.btn_w and y <= self.mouse[1]-1 <= y + self.btn_h and disable_buttons is False:
                    if prop is not None and prop[num] == 0:
                        color = rgb.red_s2
                    elif prop is not None and prop[num] == 1:
                        color = rgb.green_s2
                    elif prop is not None and prop[num] == 3:
                        if x <= self.mouse[0]-1 <= x + 40:
                            color_l = rgb.gray2
                        if x+self.btn_w-40 <= self.mouse[0]-1 <= x + self.btn_w:
                            color_r = rgb.gray2
                    else:
                        color = rgb.gray2
                        
                    # click on button
                    if self.click is True:
                        if prop is not None and prop[num] == 0:
                            color = rgb.red_s3
                        elif prop is not None and prop[num] == 1:
                            color = rgb.green_s3
                        elif prop is not None and prop[num] == 3:
                            if x <= self.mouse[0]-1 <= x + 40:
                                color_l = rgb.gray1
                            if x+self.btn_w-40 <= self.mouse[0]-1 <= x + self.btn_w:
                                color_r = rgb.gray1
                        else:
                            color = rgb.gray1
            if prop is not None and prop[num] == 4:
                color = rgb.gray2
            
            if prop is not None and prop[num] == 3:
                pygame.draw.rect(screen, rgb.gray3, (x, y, self.btn_w, self.btn_h))
                pygame.draw.rect(screen, color_l, (x, y, 40, self.btn_h))
                pygame.draw.rect(screen, color_r, (x+self.btn_w-40, y, 40, self.btn_h))
                screen.blit(self.minus, (x, y))
                screen.blit(self.plus, (x+self.btn_w-40, y))
                pygame.draw.rect(screen, rgb.white, (x, y, 40, self.btn_h), 1)
                pygame.draw.rect(screen, rgb.white, (x+self.btn_w-40, y, 40, self.btn_h), 1)
            else:
                pygame.draw.rect(screen, color, (x, y, self.btn_w, self.btn_h))
            pygame.draw.rect(screen, color_text, (x, y, self.btn_w, self.btn_h), 1)
            self.text(screen, color_text, self.fontbt, text, (x + self.btn_w/2, y + self.btn_h/2), True)
            if prop is not None and prop[num] == 2:   # from properties value add link icon
                screen.blit(self.link, (x+self.btn_w-40, y))
            y += self.btn_h + self.space   # calculate position for next button
    
    
    def buttons_horizontal(self, screen, buttons_txt, pos, prop=None, safe=False, alt_width=None):
        """Draws buttons with mouseover and self.click effect.
        Properties are passed as list with value for each button.
        Values can be: None - no effect, 0 - red color (OFF), 1 - green color (ON), 2 - add link icon on button"""
        (x, y) = pos
        btn_w = self.btn_w_h
        if alt_width is not None:
            btn_w = alt_width
        disable_buttons = False
        if safe is False:
            disable_buttons = self.disable_buttons
        for num, text in enumerate(buttons_txt):
            if prop is not None and prop[num] == 0:   # depending on properties value, determine color
                color = rgb.red_s1
            elif prop is not None and prop[num] == 1:
                color = rgb.green_s1
            else:
                color = rgb.gray3
                    
            # mouse over button
            if x <= self.mouse[0]-1 <= x + btn_w and y <= self.mouse[1]-1 <= y + self.btn_h and disable_buttons is False:
                if prop is not None and prop[num] == 0:
                    color = rgb.red_s2
                elif prop is not None and prop[num] == 1:
                    color = rgb.green_s2
                else:
                    color = rgb.gray2
                    
                # click on button
                if self.click is True:
                    if prop is not None and prop[num] == 0:
                        color = rgb.red_s3
                    elif prop is not None and prop[num] == 1:
                        color = rgb.green_s3
                    else:
                        color = rgb.gray1
                            
            pygame.draw.rect(screen, color, (x, y, btn_w, self.btn_h))
            pygame.draw.rect(screen, rgb.white, (x, y, btn_w, self.btn_h), 1)
            self.text(screen, rgb.white, self.fontbt, text, (x + btn_w/2, y + self.btn_h/2), True)
            if prop is not None and prop[num] == 2:   # from properties value add link icon
                screen.blit(self.link, (x+btn_w-40, y))
            x += btn_w + self.space   # calculate position for next button
    
    
    def buttons_list(self, screen, buttons_txt, pos, list_limit, scroll, selected, safe=False):
        """Draws buttons in scrollable list with mouseover and self.click effect."""
        (x, y) = pos
        disable_buttons = False
        if safe is False:
            disable_buttons = self.disable_buttons
        y -= scroll
        for num, text in enumerate(buttons_txt):
            if y >= pos[1] - self.btn_h - self.space:      # don't draw above list area
                color = rgb.gray3
                # mouse over button
                if pos[1] - self.space <= self.mouse[1]-1 <= pos[1] + list_limit:   # only inside list area
                    if x <= self.mouse[0]-1 <= x + self.btn_w_l and y <= self.mouse[1]-1 <= y + self.btn_h and disable_buttons is False:
                        color = rgb.gray2
                        # click on button
                        if self.click is True:
                            color = rgb.gray1
                if num == selected:
                    color = rgb.gray1
                pygame.draw.rect(screen, color, (x, y, self.btn_w_l, self.btn_h))
                pygame.draw.rect(screen, rgb.white, (x, y, self.btn_w_l, self.btn_h), 1)
                self.text(screen, rgb.white, self.fontbt, text, (x + self.btn_w_l/2, y + self.btn_h/2), True)
            y += self.btn_h + self.space   # calculate position for next button
            
            if y > pos[1] + list_limit:   # don't draw bellow list area
                break
        
        # hide buttons outside list area
        pygame.draw.rect(screen, rgb.black, (x, pos[1] - self.btn_h - self.space, self.btn_w_l, self.btn_h))
        pygame.draw.rect(screen, rgb.black, (x, pos[1] + list_limit, self.btn_w_l, self.btn_h))
        
        # scroll bar
        list_size = len(buttons_txt) * self.btn_h + len(buttons_txt) * self.space
        scrollable_len = max(0, list_size - list_limit)
        scrollbar_limit = list_limit - 40 + 4
        if scrollable_len != 0:
            scrollbar_pos = scroll * scrollbar_limit / scrollable_len
        else:
            scrollbar_pos = 0
        pygame.draw.rect(screen, rgb.gray1, (x+self.btn_w_l+self.space+2, pos[1] - self.space + 3 + scrollbar_pos, 11, 40))
        
        # list borders
        pygame.draw.rect(screen, rgb.white, (x - self.space, pos[1] - self.space, self.btn_w_l + 2*self.space, list_limit + self.space), 1)
        pygame.draw.rect(screen, rgb.white, (x - self.space, pos[1] - self.space, self.btn_w_l + 2*self.space + 16, list_limit + self.space), 1)
    
    
    def buttons_list_2col(self, screen, left_txt, right_txt, pos, list_limit, scroll, selected, safe=False):
        """Draws buttons in scrollable list with mouseover and self.click effect.
        Text is printed on 2 columns snapped to left and right button side."""
        (x, y) = pos
        disable_buttons = False
        if safe is False:
            disable_buttons = self.disable_buttons
        y -= scroll
        for num, text in enumerate(left_txt):
            if y >= pos[1] - self.btn_h - self.space:      # don't draw above list area
                color = rgb.gray3
                # mouse over button
                if pos[1] - self.space <= self.mouse[1]-1 <= pos[1] + list_limit:   # only inside list area
                    if x <= self.mouse[0]-1 <= x + self.btn_w_l and y <= self.mouse[1]-1 <= y + self.btn_h and disable_buttons is False:
                        color = rgb.gray2
                        # click on button
                        if self.click is True:
                            color = rgb.gray1
                if num == selected:
                    color = rgb.gray1
                pygame.draw.rect(screen, color, (x, y, self.btn_w_l, self.btn_h))
                pygame.draw.rect(screen, rgb.white, (x, y, self.btn_w_l, self.btn_h), 1)
                self.text(screen, rgb.white, self.fontbt, text, (x + 10, y + self.txt_y_margin))
                self.text(screen, rgb.white, self.fontbt, right_txt[num], (x + self.btn_w_l - 40, y + self.btn_h/2), True)
            y += self.btn_h + self.space   # calculate position for next button
            
            if y > pos[1] + list_limit:   # don't draw bellow list area
                break
        
        # hide buttons outside list area
        pygame.draw.rect(screen, rgb.black, (x, pos[1] - self.btn_h - self.space, self.btn_w_l, self.btn_h))
        pygame.draw.rect(screen, rgb.black, (x, pos[1] + list_limit, self.btn_w_l, self.btn_h))
        
        # scroll bar
        list_size = len(left_txt) * self.btn_h + len(left_txt) * self.space
        scrollable_len = max(0, list_size - list_limit)
        scrollbar_limit = list_limit - 40 + 4
        if scrollable_len != 0:
            scrollbar_pos = scroll * scrollbar_limit / scrollable_len
        else:
            scrollbar_pos = 0
        pygame.draw.rect(screen, rgb.gray1, (x+self.btn_w_l+self.space+2, pos[1] - self.space + 3 + scrollbar_pos, 11, 40))
        
        # list borders
        pygame.draw.rect(screen, rgb.white, (x - self.space, pos[1] - self.space, self.btn_w_l + 2*self.space, list_limit + self.space), 1)
        pygame.draw.rect(screen, rgb.white, (x - self.space, pos[1] - self.space, self.btn_w_l + 2*self.space + 16, list_limit + self.space), 1)
    
    
    def ask(self, screen, ask_txt, target, yes_txt, pos, red=False):
        """Draws window with question regarding some target, with cancel and second button with custom text and color.
        Is not affected by disabling button effects."""
        (x, y) = pos
        
        # background
        border_rect = [x-2*self.space, y-2*self.space-2*30, self.btn_w_h*2+5*self.space, 2*30+self.btn_h+4*self.space]
        bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
        pygame.draw.rect(screen, rgb.black, bg_rect)
        pygame.draw.rect(screen, rgb.white, border_rect, 1)
        
        for num, text in enumerate(["Cancel", yes_txt]):
            if num == 0:
                color = rgb.gray3
            else:
                if red is True:
                    color = rgb.red_s1
                else:
                    color = rgb.gray3
            # mouse over button
            if x <= self.mouse[0]-1 <= x + self.btn_w_h and y <= self.mouse[1]-1 <= y + self.btn_h:
                if num == 0:
                    color = rgb.gray2
                else:
                    if red is True:
                        color = rgb.red_s2
                    else:
                        color = rgb.gray2
                # click on button
                if self.click is True:
                    if num == 0:
                        color = rgb.gray1
                    else:
                        if red is True:
                            color = rgb.red_s3
                        else:
                            color = rgb.gray1
            pygame.draw.rect(screen, color, (x, y, self.btn_w_h, self.btn_h))
            pygame.draw.rect(screen, rgb.white, (x, y, self.btn_w_h, self.btn_h), 1)
            self.text(screen, rgb.white, self.fontbt, text, (x + self.btn_w_h/2, y + self.btn_h/2), True)
            x += self.btn_w_h + self.space   # calculate position for next button
        
        # text
        target = self.limit_text(target, self.fontbt, self.btn_w_h*2+5*self.space)
        self.text(screen, rgb.white, self.fontbt, ask_txt, (self.screen_x/2,  self.screen_y/2 - 40), True)
        yes_color = rgb.gray1
        if red is True:
            yes_color = rgb.red
        self.text(screen, yes_color, self.fontbt, target, (self.screen_x/2,  self.screen_y/2 - 10), True)
        
     
    def connector(self, screen, buttons_map_sel, pos_l, pos_r, bot_margin, scroll, maps, selected_item):
        (x_1, y_1) = pos_l
        (x_2, y_2) = pos_r
        right_x = x_2 - self.space
        right_y = self.screen_y/2 - bot_margin/2
        right_y_1 = y_2
        right_y_2 = right_y_1 + len(buttons_map_sel) * self.btn_h + (len(buttons_map_sel)-1) * self.space
        pygame.draw.line(screen, rgb.white, (right_x, right_y_1), (right_x, right_y_2), 2)
        
        y_pos = y_1
        y_pos -= scroll
        selected_item_pos = y_pos
        for num, text in enumerate(maps):
            if num == selected_item:
                selected_item_pos = y_pos
                break
            y_pos += self.btn_h + self.space
        left_x = x_1 + self.btn_w_l + 2*self.space + 16
        left_y = selected_item_pos + self.btn_h/2
        left_y_1 = left_y - self.btn_h/2
        left_y_2 = left_y_1 + self.btn_h
        pygame.draw.line(screen, rgb.white, (left_x, left_y_1), (left_x, left_y_2), 2)
        
        middle_x = left_x + (right_x - left_x)/2
        pygame.draw.line(screen, rgb.white, (middle_x, left_y), (middle_x, right_y), 2)
        
        pygame.draw.line(screen, rgb.white, (middle_x, right_y), (right_x, right_y), 2)
        pygame.draw.line(screen, rgb.white, (left_x, left_y), (middle_x, left_y), 2)
        
        cover_bot_y = self.screen_y-bot_margin-self.btn_h/2 + self.space
        pygame.draw.rect(screen, rgb.black, (left_x - 2, 0, middle_x-left_x+4, y_1-self.space))
        pygame.draw.rect(screen, rgb.black, (left_x - 2, cover_bot_y, middle_x-left_x+4, self.screen_y-cover_bot_y))
    
    
    def buttons_small(self, screen, imgs, pos, prop=None, selected=None):
        """Draws small square buttons with icons.
        Properties are passed as list with value for each button.
        Values can be: None - no effect, 0 - disabled button, 1 - green color (ON)"""
        (x, y) = pos
        for num, img in enumerate(imgs):
            if prop is not None and prop[num] == 1:
                color = rgb.green_s1
            else:
                color = rgb.gray3
            # mouse over button
            if x <= self.mouse[0] <= x + self.btn_s and y <= self.mouse[1] <= y + self.btn_s and self.disable_buttons is False:
                if prop is not None and prop[num] == 1:
                    color = rgb.green_s2
                else:
                    color = rgb.gray2
                # click on button
                if self.click is True:
                    if prop is not None and prop[num] == 1:
                        color = rgb.green_s3
                    else:
                        color = rgb.gray1
            if num == selected:
                color = rgb.gray1
            if prop is not None and prop[num] == 0:
                color = rgb.black
            
            pygame.draw.rect(screen, color, (x, y, self.btn_s, self.btn_s))
            screen.blit(img, (x, y))
            y += self.btn_s + 1
            pygame.draw.line(screen, rgb.white, (x, y-1), (x + self.btn_s, y-1), 1)
    
    
    def text_list(self, screen, texts, pos, size, space, imgs=None, prop=None, selected=0):
        """Draws texts in list. Optionally with icons in front of text.
        Properties are passed as list with value for each button.
        Values can be: 0 - Just print text, 1 - Editable text, 2 - 3 input values (for RGB),
        3 - Red button with larger space, 4 - green button with larger space,
        5 - icon buttons (icons passed in imgs variable, and selected button in selected variable),"""
        
        (x, y) = pos
        (w, h) = size
        for num, text in enumerate(texts):
            if prop is not None and prop[num] == 2:
                x_pos = x + 58
                for num in range(3):
                    color = rgb.gray3
                    if x_pos <= self.mouse[0]-1 <= x_pos + 53 and y <= self.mouse[1]-1 <= y + h:
                        color = rgb.gray2
                        if self.click is True:
                            color = rgb.gray1
                    pygame.draw.rect(screen, color, (x_pos, y, 53, h))
                    x_pos += 59
                self.text(screen, rgb.white, self.fontmd, "Color:   R: " + str(text[0]), (x+6, y+1))
                self.text(screen, rgb.white, self.fontmd, "G: " + str(text[1]), (x+120, y+1))
                self.text(screen, rgb.white, self.fontmd, "B: " + str(text[2]), (x+179, y+1))
            elif prop is not None and prop[num] in [1, 3, 4]:
                if prop[num] == 3:
                    color = rgb.red3
                    y += 12
                elif prop[num] == 4:
                    color = rgb.green3
                    y += 12
                else:
                    color = rgb.gray3
                if x <= self.mouse[0]-1 <= x + w and y <= self.mouse[1]-1 <= y + h:
                    if prop[num] == 3:
                        color = rgb.red_s2
                    elif prop[num] == 4:
                        color = rgb.green_s2
                    else:
                        color = rgb.gray2
                    if self.click is True:
                        if prop[num] == 3:
                            color = rgb.red_s3
                        elif prop[num] == 4:
                            color = rgb.green_s3
                        else:
                            color = rgb.gray1
                pygame.draw.rect(screen, color, (x, y, w, h))
                self.text(screen, rgb.white, self.fontmd, text, (x+6, y+1))
            elif prop is not None and prop[num] == 5:
                x_pos = x
                w_short = (w + 10) / len(imgs) - 10
                for num, img in enumerate(imgs):
                    color = rgb.gray3
                    if x_pos <= self.mouse[0]-1 <= x_pos + w_short and y <= self.mouse[1]-1 <= y + h:
                        color = rgb.gray2
                        if self.click is True:
                            color = rgb.gray1
                    pygame.draw.rect(screen, color, (x_pos, y, w_short, h))
                    if selected == num:
                        pygame.draw.rect(screen, rgb.gray1, (x_pos, y, w_short, h))
                        pygame.draw.rect(screen, rgb.white, (x_pos, y, w_short, h), 1)
                    screen.blit(imgs[num], (x_pos + w_short/2 - 10, y))
                    x_pos += w_short + 10
            else:
                self.text(screen, rgb.white, self.fontmd, text, (x+6, y+1))
            y += space
    
    
    def text_list_select(self, screen, texts, pos, size, space, selected, imgs=None):
        """Draws texts in selectable list. Optionally with icons in front of text."""
        (x, y) = pos
        (w, h) = size
        for num, text in enumerate(texts):
            color = rgb.black
            if x <= self.mouse[0]-1 <= x + w and y <= self.mouse[1]-1 <= y + h:
                color = rgb.gray2
                if self.click:
                    color = rgb.gray1
            pygame.draw.rect(screen, color, (x, y, w, h))
            if num == selected:
                pygame.draw.rect(screen, rgb.gray1, (x, y, w, h))
                pygame.draw.rect(screen, rgb.white, (x, y, w, h), 1)
            if imgs:
                screen.blit(imgs[num], (x, y))
            self.text(screen, rgb.white, self.fontmd, text, (x+h+3, y+1))
            y += space
