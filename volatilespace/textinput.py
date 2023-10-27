import pygame

from volatilespace.graphics import graphics
from volatilespace.graphics import rgb

graphics = graphics.Graphics()


class Textinput():
    def __init__(self):
        self.text = ""
        self.static_text = None
        self.textindex = 0
        self.blinking_line = True
        self.timer_hold = 0
        self.hold_first = 0.4   # delay on first step on button hold
        self.timer_repeat = 0
        self.hold_repeat = 0.04   # delay between 2 steps on button hold
        self.timer_blink = 0
        self.blinking_line_on = 0.7   # blinking line on delay
        self.blinking_line_off = 0.5   # blinking line delay off
        self.timer_double_click = 0
        self.double_click_time = 0.4   # delay for detecting double click
        self.disable_blinking_line = False
        self.backspace = False
        self.left = False
        self.right = False
        self.enable_repeat = False
        self.limit_len = None   # limit text length to n chars
        self.first_click = False   # used for detecting double click
        self.selected = False
        
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.txt_y_margin = 8  # empty space between text and button edge
        self.space = 10   # space between buttons
        self.x_corr = 0   # x axis correction for text placement
    
    
    def initial_text(self, text, static_text=None, x_corr=0, limit_len=None, selected=False):
        """Loads initial text. Static text is text that cannot be deleted and is not returned as value."""
        self.text = text   # add text
        self.textindex = len(text)   # place index at end of text
        self.lineindex = 0
        self.static_text = static_text
        self.x_corr = x_corr
        self.limit_len = limit_len
        self.first_click = True
        self.selected = selected
    
    
    def input(self, e):
        if e.type == pygame.KEYDOWN:
            
            if e.key == pygame.K_BACKSPACE:
                if self.textindex != 0:   # if there is text to delete
                    self.text = self.text[:self.textindex-1] + self.text[self.textindex:]
                    self.textindex -= 1   # move index one char left
                    self.backspace = True
                    self.disable_blinking_line = True
                if self.selected:
                    self.text = ""
                    self.textindex = 0
                    self.selected = False
            
            elif e.key == pygame.K_LEFT:
                if self.textindex != 0:   # if there is more text on left
                    self.textindex -= 1   # move index one char left
                    self.left = True
                    self.disable_blinking_line = True
                if self.selected:
                    self.textindex = 0
                    self.selected = False
            
            elif e.key == pygame.K_RIGHT:
                if self.textindex < len(self.text):   # if there is more text on right
                    self.textindex += 1   # move index one char right
                    self.right = True
                    self.disable_blinking_line = True
                if self.selected:
                    self.textindex = len(self.text)
                    self.selected = False
        
        elif e.type == pygame.KEYUP:
            # stop holding keys
            self.backspace = False
            self.left = False
            self.right = False
            self.timer_hold = 0
            self.enable_repeat = False
            self.timer_repeat = 0
            self.disable_blinking_line = False
            
        elif e.type == pygame.TEXTINPUT:
            # add char to split input buffer
            if self.limit_len is None or len(self.text) < self.limit_len:   # limit length of text
                self.text = self.text[:self.textindex] + e.text + self.text[self.textindex:]
                self.textindex += 1   # move index one char right
            if self.selected:
                self.text = e.text
                self.textindex = 1
                self.selected = False
        
        # double click on text - select all
        if e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1:
                if self.first_click:
                    self.selected = True
        
        return self.text
    
    
    def graphics(self, screen, clock, font, pos, size, center=True):
        (x, y) = pos
        (w, h) = size
        
        # draw border
        pygame.draw.rect(screen, rgb.white, (x, y, w, h), 1)
        
        text_screen = self.text
        index_screen = self.textindex
        x += self.x_corr
        
        # draw selection for left sided text
        if self.selected and not center:
            text_static = font.render(self.static_text, True, rgb.white).get_rect(midleft=(x + 6, y + h/2))
            text = font.render(text_screen, True, rgb.white)
            text_rect = text.get_rect(midleft=(x + 6 + text_static[2], y + h/2))
            pygame.draw.rect(screen, rgb.gray1, text_rect)
            
        
        # add static text
        if self.static_text:
            text_screen = self.static_text + text_screen
            index_screen += len(self.static_text)
        
        # draw centered text
        if center:
            text_rect = font.render(text_screen, True, rgb.white).get_rect(center=(0, 0))
            if text_rect[2] > w-10:   # if text is larger than input box
                while text_rect[2] > w-10:
                    text_rect = font.render(text_screen, True, rgb.white).get_rect(center=(0, 0))
                    text_rect_line = font.render((text_screen+"W")[:index_screen+1], True, rgb.white).get_rect(center=(x + w/2, y + h/2))
                    if text_rect_line[2] > w-10:   # if cursor line is over right edge
                        text_screen = text_screen[1:]   # remove 1 char from text start
                        index_screen -= 1   # and move index left
                    else:   # if cursor line is inside input box
                        text_screen = text_screen[:-1]   # remove 1 char from text end
                text = font.render(text_screen, True, rgb.white)
                text_rect = text.get_rect(midright=(x+w-10, y+h/2))   # draw text from right edge
            else:
                if self.selected:
                    text = font.render(text_screen, True, rgb.white)
                    text_rect = text.get_rect(center=(x + w/2, y + h/2))
                    pygame.draw.rect(screen, rgb.gray1, text_rect)
                text = font.render(text_screen, True, rgb.white)
                text_rect = text.get_rect(center=(x + w/2, y + h/2))   # draw centered text
            screen.blit(text, text_rect)
        else:
            text = font.render(text_screen, True, rgb.white)
            text_rect = text.get_rect(midleft=(x + 6, y + h/2))   # draw text from left edge
            screen.blit(text, text_rect)
        
        # draw blinking line
        if self.disable_blinking_line:
            self.blinking_line = True
        else:
            if self.blinking_line:
                # time from second into frames. This value is not fixed, since it can change based on fps
                time_blink = self.blinking_line_on * clock.get_fps()
            else:
                time_blink = self.blinking_line_off * clock.get_fps()
            if self.timer_blink > time_blink:
                self.blinking_line = not self.blinking_line
                self.timer_blink = 0
            self.timer_blink += 1
        if self.blinking_line is True:
            if center:
                text_rect_line = font.render(text_screen[:index_screen], True, rgb.white).get_rect(center=(x + w/2, y + h/2))
            else:
                text_rect_line = font.render(text_screen[:index_screen], True, rgb.white).get_rect(midleft=(x + 6, y + h/2))
            line_x = text_rect[0] + text_rect_line[2]
            line_y = y + h/2 - font.get_height()/2 - 1
            pygame.draw.line(screen, rgb.white, (line_x, line_y), (line_x, line_y + font.get_height() + 1))
        
        # holding keys
        if self.backspace or self.left or self.right:
            # initial long timer
            time_hold = self.hold_first * clock.get_fps()
            if self.timer_hold > time_hold:
                self.enable_repeat = True   # start repeat timer
            self.timer_hold += 1
            # repeat timer
            if self.enable_repeat:
                time_repeat = self.hold_repeat * clock.get_fps()
                if self.timer_repeat > time_repeat:
                    if self.backspace:
                        if self.textindex != 0:
                            self.text = self.text[:self.textindex-1] + self.text[self.textindex:]
                            self.textindex -= 1
                    if self.left:
                        if self.textindex != 0:
                            self.textindex -= 1
                    if self.right:
                        if self.textindex < len(self.text):
                            self.textindex += 1
                    self.timer_repeat = 0
                self.timer_repeat += 1
        
        # double click timer
        if self.first_click:
            time_double_click = self.double_click_time * clock.get_fps()
            if self.timer_double_click > time_double_click:
                self.first_click = False
                self.timer_double_click = 0
            self.timer_double_click += 1
   
