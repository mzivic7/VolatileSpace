import pygame
import math
import numpy as np
import datetime
from configparser import ConfigParser
from ast import literal_eval as leval
# import pygame_textinput   # not yet needed

from volatilespace import fileops
from volatilespace import physics_engine
from volatilespace.graphics import rgb
from volatilespace.graphics import graphics
from volatilespace.graphics import bg_stars

physics = physics_engine.Physics()
graphics = graphics.Graphics()
bg_stars = bg_stars.Bg_Stars()



class Editor():
    def __init__(self):
        self.state = 2
        self.screen_mode = False   # trigger to change screen mode
        self.fullscreen = leval(fileops.load_settings("graphics", "fullscreen"))   # is it fullscreen mode
        self.res_change = False   # cycle through resolution
        avail_res = pygame.display.list_modes()
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
        try:
            self.selected_res = avail_res.index((self.screen_x, self.screen_y))
        except Exception:   # fail-safe repair if resolution is invalid
            self.selected_res = 0   # use maximum resolution
            fileops.save_settings("graphics", "resolution", list(avail_res[0]))   # save it to file
            if self.fullscreen is True:
                pygame.display.set_mode((avail_res[0]), pygame.FULLSCREEN)
            else:
                pygame.display.set_mode((avail_res[0]))
        self.antial = leval(fileops.load_settings("graphics", "antialiasing"))   # global antialiasing
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.fontsm = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 10)   # small text font
        graphics.antial = self.antial
        
        self.ptps = 59   # divisor to convert simulation time to real time (it is not 60 because userevent timer is rounded to 17ms)
        self.zoom = 0.15   # initial zoom value
        self.key_sens = 0.02   # sensitivity when pressing or holding wasd buttons
        self.select_sens = 5   # how many pixels are tolerable for mouse to move while selecting body
        self.drag_sens = 0.02   # drag sensitivity when inserting body
        self.warp_range = [1, 2, 3, 4, 5, 10, 50, 100]   # all possible warps, by order
        self.warp_index = 0   # current warp from warp_rang
        self.sim_time = 0   # simulation time
        self.pause = False   # program paused
        self.insert_body = False   # is body being inserted
        self.move = False    # move view mode
        self.body_del = False   # which body will be deleted
        self.selected = False   # select mode
        self.direction = False   # keyboard buttons wasd
        self.follow = False   # follow selected body
        self.first = True   # is this first iterration
        self.mouse_wrap = leval(fileops.load_settings("graphics", "mouse_wrap"))   # mouse wrap
        self.mouse_raw = [0, 0]   # mouse position on screen
        self.mouse = [0, 0]   # mouse position in simulation
        self.zoom_x, self.zoom_y = 0, 0   # initial zoom offset
        self.offset_x = self.screen_x / 2   # initial centered offset to 0, 0 coordinates
        self.offset_y = self.screen_y / 2
        self.mouse_fix_x = False   # fix mouse movement when jumping off screen edge
        self.mouse_fix_y = False
        self.zoom_step = 0.05   # initial zoom step
        self.file_path = ""   # path to file to load
        self.warp = self.warp_range[self.warp_index]   # load current warp
        
        self.new_mass_init = 5   # initial mass for custom spawned objects
        self.new_density_init = 1   # initial density for custom spawned objects
        self.new_mass = self.new_mass_init   # set initial mass for custom spawned objects
        self.new_density = self.new_density_init   # set initial density for custom spawned objects
        self.new_color = (100, 100, 100)   # set initial color for custom spawned objects
        
        self.bg_stars_enable = leval(fileops.load_settings("background", "stars"))   # background stars
        self.offset_old = np.array([self.offset_x, self.offset_y])
        self.grid_enable = False   # background grid
        self.grid_mode = 0   # grid mode: 0 - global, 1 - selected body, 2 - parent
        bg_stars.set_screen()   # load pygame stuff in classes after pygame init has finished
        graphics.set_screen()
    
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()   # window width, window height
    
    
    
    ###### --Help functions-- ######
    def focus_point(self, pos, zoom=None):
        """Claculate offset and zoom, used to focus on specific coordinates"""
        if zoom:
            self.zoom = zoom
        self.offset_x = - pos[0] + self.screen_x / 2   # follow selected body
        self.offset_y = - pos[1] + self.screen_y / 2
        self.zoom_x = (self.screen_x / 2) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
        self.zoom_y = (self.screen_y / 2) - (self.screen_y / (self.zoom * 2))

    def screen_coords(self, coords_in_sim):
        """Converts from sim coords to screen coords. Adds zoom, view move, and moves origin from up-left to bottom-left"""
        x_on_screen = (coords_in_sim[0] + self.offset_x - self.zoom_x) * self.zoom   # correction for zoom, screen movement offset
        y_on_screen = (coords_in_sim[1] + self.offset_y - self.zoom_y) * self.zoom
        y_on_screen = self.screen_y - y_on_screen   # move origin from up-left to bottom-left
        return [x_on_screen, y_on_screen]
    
    def sim_coords(self, coords_on_screen):
        """Converts from screen coords to sim coords. Adds zoom, view move, and moves origin from bottom-left to up-left"""
        x_in_sim = coords_on_screen[0] / self.zoom - self.offset_x + self.zoom_x   # correction for zoom, screen movement offset
        y_in_sim = -(coords_on_screen[1] - self.screen_y) / self.zoom - self.offset_y + self.zoom_y
        # y_on_screen = y_on_screen - screen_y   move origin from bottom-left to up-left. This is implemented in above line
        return [x_in_sim, y_in_sim]
    
    
    
    ###### --Load system-- ######
    def load_system(self):
        self.sim_time, self.mass, self.density, self.position, self.velocity, self.color = fileops.load_system("system.ini")   # load initial system
        self.sim_time *= self.ptps   # convert from seconds to userevent iterations
        physics.load_system(self.mass, self.density, self.position, self.velocity, self.color)   # add it to physics class
        
        # userevent may not been run in first iteration, but this values are needed in graphics section:
        self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()   # get body information
    
    
    
    ###### --Keys-- ######
    def input_keys(self, e):
        if self.state != 2:   # when returning to editor menu
            self.state = 2   # update state
        if e.type == pygame.KEYDOWN:   # if any key is pressed:
            if e.key == pygame.K_ESCAPE:
                self.state = 1  # if "escape" key is pressed, go back to main menu
            
            if e.key == pygame.K_SPACE:   # space key
                if self.pause is False:
                    self.pause = True   # if it is not paused, pause it
                else:
                    self.pause = False  # if it is paused, unpause it
            
            if e.key == pygame.K_h:   # H key
                self.follow = False   # disable follow
                self.focus_point([0, 0], 0.5)   # return to (0,0) coordinates
                # self.zoom = 1   # reset zoom
                # self.zoom_x, self.zoom_y = 0, 0   # reset zoom offset
                
            if e.key == pygame.K_f:   # F key
                self.follow = not self.follow   # toggle follow
            
            if e.key == pygame.K_l:   # L key
                self.pause = True   # pause
                self.file_path = fileops.load_file()   # get path from load file dialog
                if self.file_path != "":   # if path is existing:
                    self.sim_time, self.mass, self.density, self.position, self.velocity, self.color = fileops.load_system(self.file_path)   # load system
                    self.sim_time *= self.ptps   # convert from seconds to userevent iterations
                    physics.load_system(self.mass, self.density, self.position, self.velocity, self.color)   # add it to physics class
                    self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()   # get information after loading
            
            if e.key == pygame.K_k:   # K key
                self.pause = True   # pause
                self.file_path = fileops.save_file(self.file_path)   # get path from save file dialog
                if self.file_path != "":   # if path is existing:
                    base_color = physics.get_base_color()
                    fileops.save_system(self.file_path, self.sim_time/self.ptps, self.mass, self.density, self.position, self.velocity, base_color)   # save system
            
            if e.key == pygame.K_p:   # P key
                self.antial = not self.antial   # flip antialiasing state
                graphics.antial = self.antial
                fileops.save_settings("graphics", "antialiasing", self.antial)   # save setting
            
            if e.key == pygame.K_b:   # B key
                self.bg_stars_enable = not self.bg_stars_enable   # flip background stars state
                fileops.save_settings("background", "stars", self.bg_stars_enable)
            
            if e.key == pygame.K_g:   # G key
                self.grid_enable = not self.grid_enable   # flip background grid state
            
            if e.key == pygame.K_v:   # V key
                if self.grid_enable is True:
                    self.grid_mode += 1   # cycle grid modes (0 - global, 1 - selected body, 2 - parent)
                    if self.grid_mode >= 3:
                        self.grid_mode = 0
            
            if e.key == pygame.K_u:   # U key
                self.screen_mode = True   # toggle screen mode (fullscreen or windowed)
                self.fullscreen = not self.fullscreen   # flip fullscreen mode flag
                fileops.save_settings("graphics", "fullscreen", self.fullscreen)
            
            if e.key == pygame.K_i:   # I key
                self.res_change = 1   # decrease resolution
            
            if e.key == pygame.K_o:   # O key
                self.res_change = -1   # increase resolution
            
            # time warp
            if e.key == pygame.K_COMMA:   # decrease
                if self.warp_index != 0:   # stop index from going out of range
                    self.warp_index -= 1   # decrease warp index
                self.warp = self.warp_range[self.warp_index]   # update warp
            if e.key == pygame.K_PERIOD:   # increase
                if self.warp_index != len(self.warp_range)-1:   # stop index from going out of range
                    self.warp_index += 1   # increase warp index
                self.warp = self.warp_range[self.warp_index]   # update warp
            if e.key == pygame.K_SLASH:   # default
                self.warp_index = 0   # reset warp index
                self.warp = self.warp_range[self.warp_index]   # update warp
            
            if self.selected is not False:   # if there is selected body, allow changing its velocity with wasd
                if e.key == pygame.K_w:
                    self.direction = "up"   # to what direction velocity is added
                if e.key == pygame.K_s:
                    self.direction = "down"
                if e.key == pygame.K_a:
                    self.direction = "left"
                if e.key == pygame.K_d:
                    self.direction = "right"
        
        if e.type == pygame.KEYUP and (e.key == pygame.K_w or e.key == pygame.K_s or e.key == pygame.K_a or e.key == pygame.K_d):
            self.direction = False   # when wasd key is released, clear direction to which velocity is added
        
        if self.direction is not False:   # add velocity to specific direction
            mass, density, temp, position, velocity, colors, size, rad_sc = physics.get_bodies()   # get body velocity to be increased
            if self.direction == "up":   # new_velocity = old_velocity + key_sensitivity
                physics.set_body_vel(self.selected, [velocity[self.selected, 0], velocity[self.selected, 1] + self.key_sens])   # set new velocity
            if self.direction == "down":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0], velocity[self.selected, 1] - self.key_sens])
            if self.direction == "left":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0] - self.key_sens, velocity[self.selected, 1]])
            if self.direction == "right":
                physics.set_body_vel(self.selected, [velocity[self.selected, 0] + self.key_sens, velocity[self.selected, 1]])
    
    
    
    ###### --Mouse-- ######
    def input_mouse(self, e):
        self.mouse_raw = list(pygame.mouse.get_pos())   # get mouse position
        self.mouse = list((self.mouse_raw[0]/self.zoom, -(self.mouse_raw[1] - self.screen_y)/self.zoom))   # mouse position on zoomed screen
        # y coordinate in self.mouse is negative for easier applying in formula to check if mouse is inside circle
        
        # left mouse button: move, select
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:   # is clicked
            self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
            self.move = True   # enable view move
            self.mouse_old = self.mouse   # initial mouse position for movement
            self.mouse_raw_old = self.mouse_raw   # initial mouse position for movement
        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:   # is released:
            self.move = False   # disable move move
            mouse_move = math.dist(self.mouse_raw, self.mouse_raw_old)   # mouse move dist
            self.select_toggle = False
            if mouse_move < self.select_sens:   # if mouse moved less than n pixels:
                for self.body, self.body_pos in enumerate(self.position):   # for each body:
                    # if mouse is inside body radius on its location: (body_x - mouse_x)**2 + (body_y - mouse_y)**2 < radius**2
                    if sum(np.square(self.body_pos - self.sim_coords(self.mouse_raw))) < (self.size[self.body])**2:
                        self.selected = self.body  # this body is selected
                        self.select_toggle = True   # do not exit select mode
                if self.select_toggle is False:   # if inside select mode
                    self.selected = False   # exit select mode
        
        # right mouse button: insert
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 3:   # is clicked
            self.insert_body = True   # start inserting body
            self.new_position = self.sim_coords(self.mouse_raw)   # first position
        if e.type == pygame.MOUSEBUTTONUP and e.button == 3 and self.insert_body is True:   # is released
            self.insert_body = False   # end inserting body
            drag_position = self.sim_coords(self.mouse_raw)   # second position
            distance = math.dist(self.new_position, drag_position) * self.zoom   # distance
            angle = math.atan2(drag_position[1] - self.new_position[1], drag_position[0] - self.new_position[0])   # angle
            new_acc = distance * self.drag_sens   # decrease acceleration to reasonable value
            new_acc_x = new_acc * math.cos(angle)   # separate acceleration components by axes
            new_acc_y = new_acc * math.sin(angle)
            new_velocity = [new_acc_x, new_acc_y]   # new velocity
            physics.add_body(self.new_mass, self.new_density, self.new_position, new_velocity, self.new_color)   # add new body to class
            self.new_mass = self.new_mass_init   # reset initial new mass
        
        # mouse wheel
        if e.type == pygame.MOUSEWHEEL and self.insert_body is True:
            if self.new_mass > 1:   # keep mass positive
                self.new_mass += e.y   # change mass
        if e.type == pygame.MOUSEWHEEL and self.insert_body is False:   # change zoom
            if self.zoom > self.zoom_step or e.y == 1:   # prevent zooming below zoom_step, zoom can't be 0, but allow zoom to increase
                self.zoom_step = self.zoom / 10   # calculate zoom_step from current zoom
                self.zoom += e.y * self.zoom_step   # add value to zoom by scrolling on mouse
                self.zoom_x += (self.screen_x / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
                self.zoom_y += (self.screen_y / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_y / (self.zoom * 2))
                # these values are added only to displayed objects, traces... But not to real position
        
        return self.state
    
    
    ###### --Physics-- ######
    def physics(self, e):
        if e.type == pygame.USEREVENT:   # event for calculations
            if self.pause is False:   # if it is not paused:
                for num in range(self.warp):
                    physics.gravity()   # do gravity physics
                    physics.body_size()   # calculate bodies radius
                    physics.body_temp()   # calculate bodies temperature
                    physics.black_hole()   # check for black holes
                    # get bodies information
                    self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()
                    
                    body_del = physics.inelastic_collision()   # collisions
                    if body_del is not False:   # if there is collision
                        self.mass, self.density, self.temp, self.position, self.velocity, self.colors, self.size, self.rad_sc = physics.get_bodies()  # get bodies information after deletion
                        if body_del == self.selected:   # if selected body is deleted:
                            self.selected = False   # exit from select mode
                        if body_del < self.selected:   # if body before selected one is deleted
                            self.selected -= 1   # on list move selected body back
                        self.direction = False   # reset wasd if not false
                    
                    self.sim_time += 1   # iterate sim_time
                    
                    if self.first is True:   # this is run only once at userevent start
                        self.first = False   # do not run it again
                        self.focus_point([0, 0], 0.5)   # initial zoom and point
                        self.selected = 1   # select body
                        self.follow = True   # follow it
        
        physics.kepler_basic()   # calculate basic keplerian elements
        self.semi_major, self.semi_minor, self.coi, self.parents = physics.get_body_orbits()   # get basic keplerian elements
        self.colors = physics.body_color()   # calculate colors from temperature
    
    
    
    ###### --Graphics-- ######
    def graphics(self, screen, clock):
        screen.fill((0, 0, 0))   # color screen black
        
        
        # follow body (this must be before drawing objects to prevent them from vibrating when moving)
        if self.follow is True and self.selected is not False:   # if follow mode is enabled
            self.offset_x = - self.position[self.selected, 0] + self.screen_x / 2   # follow selected body
            self.offset_y = - self.position[self.selected, 1] + self.screen_y / 2
        
        
        # screen movement
        if self.move is True:   # this is not in userevent to allow moving while paused
            if self.mouse_fix_x is True:   # when mouse jumps from one edge to other:
                self.mouse_old[0] = self.mouse[0]   # don't calculate that as mouse movement
                self.mouse_fix_x = False
            if self.mouse_fix_y is True:
                self.mouse_old[1] = self.mouse[1]
                self.mouse_fix_y = False
            
            mouse_move = math.dist((self.mouse_raw[0], self.mouse_raw[1]), (self.mouse_raw_old[0], self.mouse_raw_old[1]))   # distance
            self.offset_x += self.mouse[0] - self.mouse_old[0]   # add mouse movement to offset
            self.offset_y += self.mouse[1] - self.mouse_old[1]
            # save mouse position for next iteration to get movement
            # print position of view, here is not added zoom offset, this shows real position, y axis is inverted
            graphics.text(screen, rgb.white, self.fontmd, "Pos: X:" + str(int(self.offset_x - self.screen_x / 2)) + "; Y:" + str(-int(self.offset_y - self.screen_y / 2)), (300, 2))
            if mouse_move > self.select_sens:   # stop following if mouse distance is more than n pixels
                self.follow = False   # stop following selected body
            
            if self.mouse_wrap is True:
                if self.mouse_raw[0] >= self.screen_x-1:   # if mouse hits screen edge
                    pygame.mouse.set_pos(1, self.mouse_raw[1])   # move it to opposite edge ### BUG ###
                    self.mouse_fix_x = True   # in next itteration, dont calculate that as movement
                if self.mouse_raw[0] <= 0:
                    pygame.mouse.set_pos(self.screen_x, self.mouse_raw[1]-1)    # ### BUG ###
                    self.mouse_fix_x = True
                if self.mouse_raw[1] >= self.screen_y-1:
                    pygame.mouse.set_pos(self.mouse_raw[0], 1)    # ### BUG ###
                    self.mouse_fix_y = True
                if self.mouse_raw[1] <= 0:
                    pygame.mouse.set_pos(self.mouse_raw[0], self.screen_y-1)    # ### BUG ###
                    self.mouse_fix_y = True
                
            self.mouse_old = self.mouse
        
        
        # windowed / fullscreen
        if self.screen_mode is True:
            pygame.display.toggle_fullscreen()
            self.set_screen()   # change screen size in all classes that are using it
            bg_stars.set_screen()
            graphics.set_screen()
            self.screen_mode = False
        
        
        # changing resolution
        if self.res_change is not False:
            avail_res = pygame.display.list_modes()   # get available resolutions (greater index - smaller res)
            self.selected_res += self.res_change   # cycle through resolutions
            if self.selected_res > len(avail_res) - 1:   # if selected res is out of range
                self.selected_res = 0   # return it to max res
            if self.selected_res < 0:   # if selected res is negative
                self.selected_res = len(avail_res) - 1   # return it to min res
            if self.fullscreen is True:   # if previously in fullscreen, stay fullscreen
                pygame.display.set_mode((avail_res[self.selected_res]), pygame.FULLSCREEN)   # change pygame resolution
            else:
                pygame.display.set_mode((avail_res[self.selected_res]))   # change pygame resolution
            self.set_screen()   # change screen size in all classes that are using it
            bg_stars.set_screen()
            graphics.set_screen()
            self.focus_point((0, 0))   # re-calculate initial offset
            fileops.save_settings("graphics", "resolution", list(pygame.display.list_modes()[self.selected_res]))
            self.res_change = False
        
        
        # background stars:
        if self.bg_stars_enable is True:
            offset_diff = self.offset_old - np.array([self.offset_x, self.offset_y])   # movement vector in one iterration
            offset_diff = offset_diff * min(self.zoom, 3)   # add zoom to speed calculation and limit zoom
            self.offset_old = np.array([self.offset_x, self.offset_y])
            speed = math.sqrt(offset_diff.dot(offset_diff))/3   # speed as movement vector magnitude
            direction = math.atan2(offset_diff[1], offset_diff[0])   # movement vector angle from atan2
            bg_stars.draw_bg(screen, speed, direction, self.zoom)
        
        
        # background lines grid
        if self.grid_enable is True:
            if self.grid_mode == 0:   # grid mode: home
                origin = self.screen_coords([0, 0])
            if self.selected is not False:
                if self.grid_mode == 1:      # grid mode: selected body
                    if self.follow is False:
                        origin = self.screen_coords(self.position[self.selected])
                    else:   # When following body, origin is in center of screen
                        origin = [(- self.zoom_x + self.screen_x/2) * self.zoom, self.screen_y - (- self.zoom_y + self.screen_y/2) * self.zoom]
                if self.grid_mode == 2:   # grid mode: parent of selected body
                    origin = self.screen_coords(self.position[self.parents[self.selected]])
            else:
                origin = self.screen_coords([0, 0])
            graphics.draw_grid(screen, self.grid_mode, origin, self.zoom)
        
        
        # draw orbit curve lines
        curve_x, curve_y = physics.curve()   # calculate all curves
        for body in range(len(self.mass)):   # for each body:
            if body != 0:   # skip most massive body
                curve = np.column_stack(self.screen_coords(np.stack([curve_x[body], curve_y[body]])))   # get line coords on screen
                line_color = np.where(self.colors[body] > 255, 255, self.colors[body])   # get line color and limit values to top 255
                graphics.draw_lines(screen, tuple(line_color), curve, 2)   # draw that line

        
        # draw bodies
        for body in range(len(self.mass)):   # for all bodies:
            body_size = self.size[body]   # get body size
            body_color = tuple(self.colors[body])   # get color
            graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.position[body]), body_size * self.zoom)   # draw circles
            
        
        # inserting new body
        if self.insert_body is True:
            # calculate distance to current mouse position
            current_position = [(self.mouse_raw[0]/self.zoom) - self.offset_x + self.zoom_x,
                                - ((self.mouse_raw[1] - self.screen_y)/self.zoom) - self.offset_y + self.zoom_y]
            drag_distance = math.dist(self.new_position, current_position) * self.zoom
            graphics.text(screen, rgb.white, self.fontmd, "Pos: X:" + str(round(self.new_position[0])) + "; Y:" + str(round(self.new_position[1])), (300, 2))
            graphics.text(screen, rgb.white, self.fontmd, "Mass: " + str(round(self.new_mass)), (470, 2))
            graphics.text(screen, rgb.white, self.fontmd, "Acc: " + str(round(drag_distance * self.drag_sens, 2)), (560, 2))
            new_volume = self.new_mass / self.new_density   # get size of new body from mass
            new_size = (3 * new_volume / (4 * 3.14))**(1/3)   # calculate radius from volume
            # draw new body before released
            graphics.draw_circle_fill(screen, self.new_color, self.screen_coords(self.new_position), new_size * self.zoom)
            # draw line connecting body and release point
            graphics.draw_line(screen, rgb.red, self.screen_coords(self.new_position), (self.mouse_raw[0], self.mouse_raw[1]), 1)
        
        
        # select body
        if self.selected is not False:
            parent = self.parents[self.selected]      # get selected body parent
            body_pos = self.position[self.selected, :]      # get selected body position
            ecc, periapsis, apoapsis, pe_d, ap_d, distance, period, pe_t, ap_t, orb_angle, speed_orb, speed_hor, speed_vert = physics.kepler_advanced(self.selected)   # get advanced kepler parameters for selected body
            
            # circles
            graphics.draw_circle(screen, rgb.cyan, self.screen_coords(body_pos), self.size[self.selected] * self.zoom + 4, 2)   # selection circle
            if self.size[self.selected] < self.coi[self.selected]:   # if there is circle of influence, draw it
                graphics.draw_circle(screen, rgb.gray1, self.screen_coords(body_pos), self.coi[self.selected] * self.zoom + 4, 1)
            if self.selected != 0:   # skip most massive body, draw parent circle
                graphics.draw_circle(screen, rgb.red1, self.screen_coords(self.position[parent]), self.size[parent] * self.zoom + 4, 1)
                if parent != 0:   # if parent is not most massive body, draw parent circle of influence
                    graphics.draw_circle(screen, rgb.red1, self.screen_coords(self.position[parent]), self.coi[parent] * self.zoom + 4, 1)
            
            # ap and pe
            if not ecc > 1:   # if orbit is not parabola or hyperbola
                if ecc != 0:   # if orbit is not circle
                    # periapsis location marker, text: distance and time to it
                    pe_scr = self.screen_coords(periapsis)   # periapsis screen coords
                    graphics.draw_circle_fill(screen, rgb.lime1, pe_scr, 3)   # periapsis marker
                    graphics.text(screen, rgb.lime1, self.fontsm, "Periapsis: " + str(round(pe_d, 1)), (pe_scr[0], pe_scr[1] + 7), True)
                    graphics.text(screen, rgb.lime1, self.fontsm, "T - " + str(datetime.timedelta(seconds=round(pe_t/self.ptps))), (pe_scr[0], pe_scr[1] + 17), True)
                
                if ecc < 1:   # if orbit is ellipse
                    # apoapsis location marker, text: distance and time to it
                    ap_scr = self.screen_coords(apoapsis)   # apoapsis with zoom and offset
                    graphics.draw_circle_fill(screen, rgb.lime1, ap_scr, 3)   # apoapsis marker
                    graphics.text(screen, rgb.lime1, self.fontsm, "Apoapsis: " + str(round(ap_d, 1)), (ap_scr[0], ap_scr[1] + 7), True)
                    graphics.text(screen, rgb.lime1, self.fontsm, "T - " + str(datetime.timedelta(seconds=round(ap_t/self.ptps))), (ap_scr[0], ap_scr[1] + 17), True)
        
        
        # print basic data
        graphics.timed_text(screen, clock)   # timed text on screen
        graphics.text(screen, rgb.white, self.fontmd, str(datetime.timedelta(seconds=round(self.sim_time/self.ptps))), (2, 2))
        if self.pause is True:   # if paused
            graphics.text(screen, rgb.red1, self.fontmd, "PAUSED", (70, 2))
        else:
            graphics.text(screen, rgb.white, self.fontmd, "Warp: x" + str(int(self.warp)), (70, 2))
        if self.zoom < 10:   # rounding zoom to use max 4 chars (dot included)
            zoom_round = round(self.zoom, 2)
        elif self.zoom < 100:
            zoom_round = round(self.zoom, 1)
        elif self.zoom < 1000:
            zoom_round = int(self.zoom)
        else:
            zoom_round = "999+"
        graphics.text(screen, rgb.white, self.fontmd, "Zoom: x" + str(zoom_round), (160, 2))
        graphics.text(screen, rgb.gray, self.fontmd, str(self.mouse_raw), (self.screen_x - 100, self.screen_y - 60))
        graphics.text(screen, rgb.gray, self.fontmd, "(" + str(int(self.sim_coords(self.mouse_raw)[0])) + ", " + str(int(self.sim_coords(self.mouse_raw)[1])) + ")", (self.screen_x - 100, self.screen_y - 40))
        graphics.text(screen, rgb.gray, self.fontmd, "fps: " + str(int(clock.get_fps())), (self.screen_x - 60, self.screen_y - 20))
    
    
    
    ###### --Menus-- ######
    def gui(self):
        pass
