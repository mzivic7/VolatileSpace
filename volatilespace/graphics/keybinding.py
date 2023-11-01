import sys
import pygame

from volatilespace import fileops
from volatilespace.graphics import graphics
from volatilespace.graphics import rgb

graphics = graphics.Graphics()

buttons_keyb_ui = ["Accept", "Cancel", "Load default"]


class Keybinding():
    def __init__(self):
        self.run = True
        self.keyb_dict = fileops.load_keybindings()
        self.disable_buttons = False
        self.mouse = [0, 0]
        self.click = False
        self.scroll = 0
        self.scroll_sens = 10
        self.scrollbar_drag = False
        self.scrollbar_drag_start = 0
        self.selected_item = None
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.txt_y_margin = 8  # empty space between text and button edge
        self.btn_h = self.fontbt.get_height() + self.txt_y_margin * 2   # button height from font height
        self.space = 10   # space between buttons
        self.bot_margin = 60
        self.top_margin = 60
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.keyb_y_ui = self.screen_y - self.bot_margin
        self.keyb_x_ui = self.screen_x/2 - (len(buttons_keyb_ui) * self.btn_w_h + (len(buttons_keyb_ui)-1) * self.space)/2
        self.keyb_x = self.screen_x/2 - self.btn_w_l/2
        self.keyb_y = self.top_margin
        self.keyb_max_y = self.screen_y - 200
        self.list_limit = self.keyb_y_ui - self.keyb_y - self.space - 12
        self.list_size = len(self.keyb_dict) * self.btn_h + len(self.keyb_dict) * self.space
        self.keybindings_for_screen()
    
    
    def keybindings_for_screen(self):
        """Generate keybindings list for displaying on screen"""
        keyb_list = list(self.keyb_dict.keys())
        val_list = list(self.keyb_dict.values())
        self.key_list_screen = []
        self.val_list_screen = []
        # keys list
        for item in keyb_list:
            item = item.replace("_", " ").replace("ui", "UI").capitalize()
            self.key_list_screen.append(item)
        # values list
        for value in val_list:
            value_text = pygame.key.name(int(value)).replace("left ", "L ").replace("right", "R ").replace(" lock", "").title()
            self.val_list_screen.append(value_text)
        

    
    def input_keys(self, e):
        """Keyboard input"""
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.run = False
                self.scrollbar_drag = False
            else:
                if self.selected_item is not None:
                    # update keybindings list by index from selected item
                    key = list(self.keyb_dict)[self.selected_item]   # get key from index
                    self.keyb_dict[key] = e.key
                    self.keybindings_for_screen()
                    self.selected_item = None
    
    
    def input_mouse(self, e):
        """Mouse input"""
        self.mouse = list(pygame.mouse.get_pos())
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click = True
            
            # scroll bar
            scrollable_len = max(0, self.list_size - self.list_limit)
            scrollbar_limit = self.list_limit - 40 + 4
            if scrollable_len != 0:
                scrollbar_pos = self.scroll * scrollbar_limit / scrollable_len
            else:
                scrollbar_pos = 0
            scrollbar_y = self.keyb_y - self.space + 3 + scrollbar_pos
            scrollbar_x = self.keyb_x + self.btn_w_l + self.space + 2
            if scrollbar_x <= self.mouse[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse[1]-1 <= scrollbar_y + 40:
                self.scrollbar_drag = True
                self.scrollbar_drag_start = self.mouse[1]
                self.disable_buttons = True
        
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.click is True:
                if self.disable_buttons is False:
                
                    # list
                    if self.keyb_y - self.space <= self.mouse[1]-1 <= self.keyb_y + self.list_limit:
                        y_pos = self.keyb_y - self.scroll
                        for num, _ in enumerate(self.keyb_dict):
                            # don't detect outside list area
                            if y_pos >= self.keyb_y - self.btn_h - self.space and y_pos <= self.keyb_y + self.list_limit:
                                if self.keyb_x <= self.mouse[0]-1 <= self.keyb_x + self.btn_w_l and y_pos <= self.mouse[1]-1 <= y_pos + self.btn_h:
                                    self.selected_item = num
                            y_pos += self.btn_h + self.space
                    
                    # ui
                    x_pos = self.keyb_x_ui
                    for num, _ in enumerate(buttons_keyb_ui):
                        if x_pos <= self.mouse[0]-1 <= x_pos + self.btn_w_h and self.keyb_y_ui <= self.mouse[1]-1 <= self.keyb_y_ui + self.btn_h:
                            if num == 0:   # apply
                                fileops.save_keybindings(self.keyb_dict)
                                self.run = False
                            elif num == 1:   # cancel
                                self.run = False
                            elif num == 2:   # load default
                                fileops.default_keybindings()
                        x_pos += self.btn_w_h + self.space
                
                if self.scrollbar_drag is True:   # disable scrollbar_drag when release click
                    self.scrollbar_drag = False
                    self.disable_buttons = False
                
                self.click = False
        
        # moving scrollbar with cursor
        if self.scrollbar_drag is True:
            scrollbar_pos = self.mouse[1] - self.keyb_y
            scrollable_len = max(0, self.list_size - self.list_limit)
            scrollbar_limit = self.list_limit - 40 + 4
            self.scroll = scrollable_len * scrollbar_pos / scrollbar_limit
            if self.scroll < 0:
                self.scroll = 0
            elif self.scroll > max(0, self.list_size - self.list_limit):
                self.scroll = max(0, self.list_size - self.list_limit)
        
        if e.type == pygame.MOUSEWHEEL:
            if self.scrollbar_drag is False:
                # scrolling inside list area
                if self.keyb_x-self.space <= self.mouse[0]-1 <= self.keyb_x+self.btn_w_l+self.space+16 and self.keyb_y-self.space <= self.mouse[1]-1 <= self.keyb_y+self.list_limit:
                    self.scroll -= e.y * self.scroll_sens
                    if self.scroll < 0:
                        self.scroll = 0
                    elif self.scroll > max(0, self.list_size - self.list_limit):
                        self.scroll = max(0, self.list_size - self.list_limit)
        
        graphics.update_mouse(self.mouse, self.click, self.disable_buttons)
        return self.run
    
    
    def gui(self, screen):
        """Draw buttons"""
        screen.fill((0, 0, 0))
        
        graphics.buttons_list_2col(screen, self.key_list_screen, self.val_list_screen, (self.keyb_x, self.keyb_y), self.list_limit, self.scroll, self.selected_item)
        graphics.buttons_horizontal(screen, buttons_keyb_ui, (self.keyb_x_ui, self.keyb_y_ui))
        
        if self.selected_item is not None:
            graphics.text(screen, rgb.red, self.fontmd, "Press key you want to bind.", (self.screen_x/2, self.keyb_y_ui-12), True)




def main(screen, clock):
    """Main loop for keybindings menu"""
    keybindings = Keybinding()
    run = True
    while run:
        for e in pygame.event.get():
            keybindings.input_keys(e)
            run = keybindings.input_mouse(e)
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        keybindings.gui(screen)
        pygame.display.flip()
        clock.tick(60)
