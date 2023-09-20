import pygame

from volatilespace.graphics import graphics
from volatilespace.graphics import rgb

graphics = graphics.Graphics()


class Textinput():
    def __init__(self):
        self.text = ""
        self.textindex = 0
        self.blinking_line = True
        self.timer_hold = 0
        self.hold_first = 40   # delay on first step on button hold  (ms)
        self.timer_repeat = 0
        self.hold_repeat = 4   # delay between 2 steps on button hold
        self.timer_blink = 0
        self.blinking_line_on = 70   # blinking line on delay
        self.blinking_line_off = 50   # blinking line delay off
        self.disable_blinking_line = False
        self.backspace = False
        self.left = False
        self.right = False
        self.enable_repeat = False
        
        
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.txt_y_margin = 8  # empty space between text and button edge
        self.font_h = self.fontbt.get_height()
        self.btn_h = self.font_h + self.txt_y_margin * 2   # button height from font height
        self.space = 10   # space between buttons
    
    
    def initial_text(self, text):
        """Loads initial text."""
        self.text = text   # add text
        self.textindex = len(text)   # place index at end of text
        self.lineindex = 0
    
    
    def input_keys(self, e):
        if e.type == pygame.KEYDOWN:
            
            if e.key == pygame.K_BACKSPACE:
                if self.textindex != 0:   # if there is text to delete
                    self.text = self.text[:self.textindex-1] + self.text[self.textindex:]
                    self.textindex -= 1   # move index one char left
                    self.backspace = True
                    self.disable_blinking_line = True
            
            elif e.key == pygame.K_LEFT:
                if self.textindex != 0:   # if there is more text on left
                    self.textindex -= 1   # move index one char left
                    self.left = True
                    self.disable_blinking_line = True
            
            elif e.key == pygame.K_RIGHT:
                if self.textindex < len(self.text):   # if there is more text on right
                    self.textindex += 1   # move index one char right
                    self.right = True
                    self.disable_blinking_line = True
        
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
            # max_width = 300
            # text_rect = self.fontbt.render(self.text, True, rgb.white).get_rect(center=(0, 0))
            # if text_rect[2] < max_width-10:
            self.text = self.text[:self.textindex] + e.text + self.text[self.textindex:]
            self.textindex += 1   # move index one char right
        
        return self.text
    
    
    def input_mouse(self, e):
        # ### TODO ###
        # click on text - change cursor position
        # click outside box - save
        # select with mouse
        # delete replace selection
        # double click on text - select all
        pass
    
    
    def graphics(self, screen, clock, pos, size):
        (x, y) = pos
        (w, h) = size
        
        # draw border
        pygame.draw.rect(screen, rgb.white, (x, y, w, self.btn_h), 1)
        
        # draw text
        text_screen = self.text
        index_screen = self.textindex
        text_rect = self.fontbt.render(text_screen, True, rgb.white).get_rect(center=(0, 0))
        if text_rect[2] > w-10:   # if text is larger than input box
            while text_rect[2] > w-10:
                text_rect = self.fontbt.render(text_screen, True, rgb.white).get_rect(center=(0, 0))
                text_rect_line = self.fontbt.render(text_screen[:index_screen], True, rgb.white).get_rect(center=(x + w/2, y + h/2))
                if text_rect_line[2] > w-10:   # if cursor line is over right edge
                    text_screen = text_screen[1:]   # remove 1 char from text start
                    index_screen -= 1   # and move index left
                else:   # if cursor line is inside input box
                    text_screen = text_screen[:-1]   # remove 1 char from text end
            text = self.fontbt.render(text_screen, True, rgb.white)
            text_rect = text.get_rect(midright=(x+w-10, y+h/2))   # draw text from right edge
        else:
            text = self.fontbt.render(text_screen, True, rgb.white)
            text_rect = text.get_rect(center=(x + w/2, y + h/2))   # draw centered text
        screen.blit(text, text_rect)
        
        # draw blinking line
        if self.disable_blinking_line:
            self.blinking_line = True
        else:
            if self.blinking_line:
                # time from second into frames. This value is not fixed, since it can change based on fps
                time_blink = self.blinking_line_on / 100 * clock.get_fps()
            else:
                time_blink = self.blinking_line_off / 100 * clock.get_fps()
            if self.timer_blink > time_blink:
                self.blinking_line = not self.blinking_line
                self.timer_blink = 0
            self.timer_blink += 1
        if self.blinking_line is True:
            text_rect_line = self.fontbt.render(text_screen[:index_screen], True, rgb.white).get_rect(center=(x + w/2, y + h/2))
            line_x = text_rect[0] + text_rect_line[2]
            line_y = y + h/2 - self.font_h/2 - 1
            pygame.draw.line(screen, rgb.white, (line_x, line_y), (line_x, line_y + self.font_h - 1))
        
        # holding keys
        if self.backspace or self.left or self.right:
            # initial long timer
            time_hold = self.hold_first / 100 * clock.get_fps()
            if self.timer_hold > time_hold:
                self.enable_repeat = True   # start repeat timer
            self.timer_hold += 1
            # repeat timer
            if self.enable_repeat:
                time_repeat = self.hold_repeat / 100 * clock.get_fps()
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
