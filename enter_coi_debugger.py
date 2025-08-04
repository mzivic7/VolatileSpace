import argparse
import importlib
import math
import os
import sys
import time
import traceback
from configparser import ConfigParser

import numpy as np
import pygame

import volatilespace.physics.orbit_intersect_debug
from volatilespace.graphics import graphics, rgb
from volatilespace.physics.orbit_intersect_debug import predict_enter_coi
from volatilespace.physics.phys_shared import curve_points, orb2xy

CURVE_POINTS_NUM = 500
V_RADIUS = 1
B_RADIUS = 20
REF_RADIUS = 50
VSYNC = True
ANTIALIASING = True
TEXT_GRID_MODE = ["Disabled", "Global", "Vessel"]
VERSION = "0.5.2"

v_radius = max(2, V_RADIUS)
b_radius = max(20, B_RADIUS)
v_note_offset = (v_radius + 5) * math.sin(np.pi / 4)


def simulate(ini_path):
    """Run enter-COI prediction algorithm and return its log path"""
    # load data from ini
    try:
        data = ConfigParser()
        data.read(ini_path)
        v_ecc = float(data.get("vessel", "ecc"))
        v_ma = float(data.get("vessel", "ma"))
        v_ea = float(data.get("vessel", "ea"))
        v_pea = float(data.get("vessel", "pea"))
        v_a = float(data.get("vessel", "a"))
        v_b = float(data.get("vessel", "b"))
        v_f = float(data.get("vessel", "f"))
        v_period = float(data.get("vessel", "period"))
        v_dr = float(data.get("vessel", "dr"))
        ref_coi = float(data.get("vessel", "ref_coi"))
        vessel_data = (v_ecc, v_ma, v_ea, v_pea, 0.0, v_a, v_b, v_f, v_period, ref_coi, v_dr)
        b_ecc = float(data.get("body", "ecc"))
        b_ma = float(data.get("body", "ma"))
        b_pea = float(data.get("body", "pea"))
        b_n = float(data.get("body", "n"))
        b_a = float(data.get("body", "a"))
        b_b = float(data.get("body", "b"))
        b_f = float(data.get("body", "f"))
        b_dr = float(data.get("body", "dr"))
        b_coi = float(data.get("body", "coi"))
        body_data = (b_ecc, b_ma, 0.0, b_pea, b_n, b_a, b_b, b_f, 0.0, b_dr, b_coi)
    except Exception as e:
        print("Error reading file:")
        print(e)
        sys.exit()
    center_x = v_f * math.cos(v_pea)
    center_y = v_f * math.sin(v_pea)
    vessel_orbit_center = (center_x, center_y)
    date = time.strftime("%Y-%m-%d_%H-%M-%S")
    nice_date = time.strftime("%Y.%m.%d %H:%M:%S")
    log_name = f"enter_coi_debug_{date}.log"
    if not os.path.exists("Logs"):
        os.mkdir("Logs")
    log_path = os.path.join("Logs", log_name)
    temp = sys.stdout
    sys.stdout = open(log_path, "wt")
    print("-----------------------SYSTEM-----------------------")
    print(f"Volatile Space: v{VERSION}")
    print(f"Python: {sys.version.split(" ")[0]}")
    print(f"Numpy: {np.version.version}")
    print(f"Time: {nice_date}")
    _ = predict_enter_coi(vessel_data, body_data, vessel_orbit_center, np.nan)
    sys.stdout = temp
    return log_path


def curve_move_to(curve, f, pea):
    """Move curve to given periapsis and focus point"""
    return curve + np.array([math.cos(pea), math.sin(pea)]) * f



class Debugger():
    """Debugger class"""
    def __init__(self):
        self.ptps = 58.823   # divisor to convert simulation time to real time (it is not 60 because userevent timer is rounded to 17ms)
        self.zoom = 0.15
        self.select_sens = 5   # how many pixels are tolerable for mouse to move while selecting body
        self.drag_sens = 0.02   # drag sensitivity when inserting body
        self.sim_time = 0
        self.move = False
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.screen_dim = np.array([self.screen_x, self.screen_y])
        self.mouse = [0, 0]   # in simulation
        self.mouse_raw = [0, 0]   # on screen
        self.offset_x = self.screen_x / 2   # initial centered offset to 0, 0 coordinates
        self.offset_y = self.screen_y / 2
        self.mouse_fix_x = False   # fix mouse movement when jumping off screen edge
        self.mouse_fix_y = False
        self.zoom_step = 0.05
        self.zoom_x = (self.screen_x / 2) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
        self.zoom_y = (self.screen_y / 2) - (self.screen_y / (self.zoom * 2))
        self.t = np.linspace(-np.pi, np.pi, CURVE_POINTS_NUM)   # parameter
        self.grid_mode = 0   # grid mode: 0 - global, 1 - selected body, 2 - parent
        self.screenshot = False
        self.ini_path = None
        self.iteration = 0
        self.show_log = True
        self.opposed = False
        self.system_text = ""
        self.data_text = "INPUT DATA:\n"
        self.end_text = "OUTPUT DATA:\n"
        self.probe_text = "PROBE POINTS:\n"
        self.search_text = "PROBING:\n"
        self.iteration_texts = []
        self.v_ea = []
        self.b_ea = []
        self.v_end_ea = np.nan
        self.b_end_ea = np.nan
        self.past_v_ea = []
        self.past_b_ea = []
        self.intersections = []
        graphics.antial = ANTIALIASING
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 12)
        self.fontsm = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 10)
        graphics.set_screen()


    def screen_coords(self, coords_in_sim):
        """Calculate screen coords from simulation coords"""
        # correction for zoom, screen movement offset
        x_on_screen = (coords_in_sim[0] + self.offset_x - self.zoom_x) * self.zoom
        y_on_screen = (coords_in_sim[1] + self.offset_y - self.zoom_y) * self.zoom
        # move origin from up-left to bottom-left
        y_on_screen = self.screen_y - y_on_screen
        return np.array([x_on_screen, y_on_screen])


    def screen_coords_array(self, coords_in_sim):
        """Calculate screen coords from simulation coords, for array"""
        x_on_screen = (coords_in_sim[:, 0] + self.offset_x - self.zoom_x) * self.zoom
        y_on_screen = (coords_in_sim[:, 1] + self.offset_y - self.zoom_y) * self.zoom
        y_on_screen = self.screen_y - y_on_screen
        return np.column_stack([x_on_screen, y_on_screen])


    def focus_point(self, pos, zoom=None):
        """Move screen view to given point and zoom"""
        if zoom:
            self.zoom = zoom
        self.offset_x = - pos[0] + self.screen_x / 2   # follow selected body
        self.offset_y = - pos[1] + self.screen_y / 2
        self.zoom_x = (self.screen_x / 2) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
        self.zoom_y = (self.screen_y / 2) - (self.screen_y / (self.zoom * 2))


    def read_log(self, log_path, ini_path):
        """Read enter-COI log and prepare data for graphical representation"""
        self.screenshot = False
        self.iteration = 0
        self.show_log = True
        self.opposed = False
        self.system_text = ""
        self.data_text = "INPUT DATA:\n"
        self.end_text = "OUTPUT DATA:\n"
        self.probe_text = "PROBE POINTS:\n"
        self.search_text = "PROBING:\n"
        self.iteration_texts = []
        self.v_ea = []
        self.b_ea = []
        self.v_end_ea = np.nan
        self.b_end_ea = np.nan
        self.past_v_ea = []
        self.past_b_ea = []
        self.intersections = []
        self.iteration_types = []
        self.ini_path = ini_path
        with open(log_path, "r") as f:
            raw_text = f.readlines()
        text = []
        for line in raw_text:
            if line == "-----CORRECTION CHECK-----\n":
                text.append("CORRECTION CHECK")
            else:
                text.append(line.replace("\n", ""))
        keys = []
        key_lines = []
        for num, line in enumerate(text):
            if line[:3] == "---":
                keys.append(line.replace("-", ""))
                key_lines.append(num)
        key_lines.append(num)
        for num, key in enumerate(keys):
            line_num = key_lines[num]
            next_line_num = key_lines[num + 1]
            if key == "SYSTEM":
                for line in text[line_num+1:next_line_num]:
                    if line != "":
                        self.system_text += line + "\n"

            if key == "DATA":
                for line in text[line_num+1:next_line_num]:
                    if line.startswith("ecc = "):
                        v_ecc = float(line.replace("ecc = ", ""))
                    elif line.startswith("ea = "):
                        self.v_init_ea = float(line.replace("ea = ", ""))
                    elif line.startswith("pea = "):
                        v_pea = float(line.replace("pea = ", ""))
                    elif line.startswith("a = "):
                        v_a = float(line.replace("a = ", ""))
                    elif line.startswith("b = "):
                        v_b = float(line.replace("b = ", ""))
                    elif line.startswith("f = "):
                        v_f = float(line.replace("f = ", ""))
                    elif line.startswith("b_ecc = "):
                        b_ecc = float(line.replace("b_ecc = ", ""))
                    elif line.startswith("b_ea = "):
                        self.v_init_ea = float(line.replace("b_ea = ", ""))
                    elif line.startswith("b_pea = "):
                        b_pea = float(line.replace("b_pea = ", ""))
                    elif line.startswith("b_a = "):
                        b_a = float(line.replace("b_a = ", ""))
                    elif line.startswith("b_b = "):
                        b_b = float(line.replace("b_b = ", ""))
                    elif line.startswith("b_f = "):
                        b_f = float(line.replace("b_f = ", ""))
                    elif line.startswith("b_f = "):
                        b_f = float(line.replace("b_f = ", ""))
                    elif line.startswith("b_coi = "):
                        self.b_coi = float(line.replace("b_coi = ", ""))
                    elif "OPPOSED" in line:
                        self.opposed = True
                    if line != "":
                        if line.startswith("dr = "):
                            if float(line.replace("dr = ", "")) > 0:
                                self.data_text += "direction = Counter-Clockwise\n"
                            else:
                                self.data_text += "direction = Clockwise\n"
                        if line.startswith("b_dr = "):
                            if float(line.replace("b_dr = ", "")) > 0:
                                self.data_text += "body direction = Counter-Clockwise\n"
                            else:
                                self.data_text += "body direction = Clockwise\n"
                        else:
                            self.data_text += line + "\n"

            if key == "GENERATING PROBE POINTS":
                for line in text[line_num+1:next_line_num]:
                    if line != "":
                        self.probe_text += line + "\n"

            if key == "SEARCHING FOR INIT INTERSECTION":
                search_start = None
                for num_1, line in enumerate(text[line_num+1:next_line_num]):
                    if line.startswith("new_ma = "):
                        if not search_start:
                            search_start = line_num+1 + num_1
                        search_end = line_num+1 + num_1
                new_search_start = search_start
                if search_end - search_start > 10:
                    new_search_start = search_end - 10
                for line in text[line_num+1:search_start] + text[new_search_start:next_line_num]:
                    if line != "":
                        self.search_text += line + "\n"

            if key == "END":
                for line in text[line_num+1:next_line_num+1]:
                    if line.startswith("new_ea = "):
                        self.v_end_ea = float(line.replace("new_ea = ", "").split(" rad")[0])
                    if line != "":
                        self.end_text += line + "\n"

            if "ITERATION" in key:
                iteration_text = ""
                iteration_type = 0
                if self.opposed and len(self.iteration_types) == 0:
                    iteration_type = 1
                for line in text[line_num+1:next_line_num]:
                    if line.startswith("new_ea = "):
                        self.v_ea.append(float(line.replace("new_ea = ", "").replace(" rad", "")))
                    elif line.startswith("new_b_ea = "):
                        self.b_ea.append(float(line.replace("new_b_ea = ", "").replace(" rad", "")))
                    elif line.startswith("intersections_ea: "):
                        intersections_str = line.replace("intersections_ea: [", "").replace("] rad", "")
                        intersections_str = intersections_str.split(" ")
                        self.intersections.append([float(x) for x in intersections_str if x != ""])
                    elif "OPPOSED" in line:
                        if "FIRST" in line:
                            iteration_type = 1
                        elif "SECOND" in line:
                            iteration_type = 2
                    elif "LOST" in line:
                        iteration_type = 3
                        self.intersections.append([np.nan])
                    if line != "" and not line.startswith("iteration time") and "OPPOSED" not in line:
                        iteration_text += line + "\n"
                self.iteration_texts.append(iteration_text)
                self.iteration_types.append(iteration_type)

        if not self.v_ea:
            self.v_ea = [self.v_init_ea]
            self.b_ea = [np.nan]
            self.intersections = [[np.nan, np.nan]]
            self.iteration_texts = [self.end_text.replace("OUTPUT DATA:\n", "")]

        # generate orbit curves
        b_curve = curve_points(b_ecc, b_a, b_b, b_pea, self.t)
        v_curve = curve_points(v_ecc, v_a, v_b, v_pea, self.t)
        self.b_curve = curve_move_to(b_curve, b_f, b_pea)
        self.v_curve = curve_move_to(v_curve, v_f, v_pea)

        # initial zoom
        v_ap = v_a * (1 + v_ecc)
        b_ap = b_a * (1 + b_ecc)
        max_ap = max(v_ap, b_ap)
        self.init_zoom = (self.screen_y - 120) / (max_ap * 2)
        self.focus_point([0, 0], self.init_zoom)

        self.b_a, self.b_b, self.b_f, self.b_ecc, self.b_pea = b_a, b_b, b_f, b_ecc, b_pea
        self.v_a, self.v_b, self.v_f, self.v_ecc, self.v_pea = v_a, v_b, v_f, v_ecc, v_pea

        # calculate initial coordinates
        self.v_init_pos = orb2xy(v_a, v_b, v_f, v_ecc, v_pea, [0, 0], self.v_init_ea)
        self.v_end_pos = orb2xy(v_a, v_b, v_f, v_ecc, v_pea, [0, 0], self.v_end_ea)
        self.iterate_log()

        # calculate iterations coordinates
        self.b_pos = []
        for b_ea in self.b_ea:
            b_pos = orb2xy(self.b_a, self.b_b, self.b_f, self.b_ecc, self.b_pea, [0, 0], b_ea)
            self.b_pos.append(b_pos)
        self.v_pos = []
        for v_ea in self.v_ea:
            v_pos = orb2xy(self.v_a, self.v_b, self.v_f, self.v_ecc, self.v_pea, [0, 0], v_ea)
            self.v_pos.append(v_pos)


    def iterate_log(self):
        """Get data from one log iteration, after read_log()"""
        self.intersections_pos = []
        for intersection in self.intersections[self.iteration]:
            pos = orb2xy(self.v_a, self.v_b, self.v_f, self.v_ecc, self.v_pea, [0, 0], intersection)
            self.intersections_pos.append(pos)


    def input_keys(self, e):
        """Handle keyboard events"""
        if e.type == pygame.KEYDOWN:

            if e.key in (pygame.K_RIGHT, pygame.K_DOWN):
                if self.iteration < len(self.b_ea) - 1:
                    self.iteration += 1
                    self.iterate_log()

            elif e.key in (pygame.K_LEFT, pygame.K_UP):
                if self.iteration > 0:
                    self.iteration -= 1
                    self.iterate_log()

            elif e.key == pygame.K_g:
                self.grid_mode += 1   # cycle grid modes (0-disabled, 1-global, 2-vessel)
                if self.grid_mode > 2:
                    self.grid_mode = 0
                text = TEXT_GRID_MODE[self.grid_mode]
                graphics.timed_text_init(
                    rgb.gray0, self.fontmd,
                    "Grid: " + text,
                    (self.screen_x/2, self.screen_y-70), 1.5, True,
                )

            elif e.key == pygame.K_h:
                self.focus_point([0, 0], self.init_zoom)

            elif e.key == pygame.K_t:
                self.show_log = not self.show_log

            elif e.key == pygame.K_r:
                if self.ini_path:
                    try:
                        importlib.reload(volatilespace.physics.orbit_intersect_debug)
                        log_path = simulate(self.ini_path)
                        self.read_log(log_path, self.ini_path)
                        graphics.timed_text_init(
                            rgb.gray0, self.fontmd,
                            "Re-running simulation... New log has been created and loaded",
                            (self.screen_x/2, self.screen_y-70), 2, True,
                        )
                    except KeyboardInterrupt:
                        sys.exit()
                    except Exception:
                        graphics.timed_text_init(
                            rgb.red, self.fontmd,
                            "Error in orbit_intersect_debug.py, log not loaded, check cmd output for traceback",
                            (self.screen_x/2, self.screen_y-70), 2, True,
                        )
                        print(traceback.format_exc())
                else:
                    graphics.timed_text_init(
                        rgb.gray0, self.fontmd,
                        "Unable to re-run simulation - ini file not provided",
                        (self.screen_x/2, self.screen_y-70), 2, True,
                    )

            elif e.key == pygame.K_F1:
                self.screenshot = True


    def input_mouse(self, e):
        """Handle mouse events"""
        self.mouse_raw = list(pygame.mouse.get_pos())
        self.mouse = list((self.mouse_raw[0]/self.zoom, -(self.mouse_raw[1] - self.screen_y)/self.zoom))

        # moving with lclick
        if e.type == pygame.MOUSEBUTTONDOWN:
            if e.button == 1:
                self.move = True
                self.mouse_old = self.mouse
        if e.type == pygame.MOUSEBUTTONUP:
            if e.button == 1:
                self.move = False

        # mouse wheel: change zoom
        if e.type == pygame.MOUSEWHEEL:
            if self.zoom > self.zoom_step or e.y == 1:   # prevent zooming below zoom_step, zoom can't be 0, but allow zoom to increase
                self.zoom_step = self.zoom / 10
                self.zoom += e.y * self.zoom_step
                # zoom translation to center
                self.zoom_x += (self.screen_x / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_x / (self.zoom * 2))
                self.zoom_y += (self.screen_y / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_y / (self.zoom * 2))


    def graphics(self, screen):
        """Draw graphics"""
        screen.fill((0, 0, 0))

        # screen movement
        if self.move:
            if self.mouse_fix_x:   # when mouse jumps from one edge to other:
                self.mouse_old[0] = self.mouse[0]   # don't calculate that as mouse movement
                self.mouse_fix_x = False
            if self.mouse_fix_y:
                self.mouse_old[1] = self.mouse[1]
                self.mouse_fix_y = False

            self.offset_x += self.mouse[0] - self.mouse_old[0]   # add mouse movement to offset
            self.offset_y += self.mouse[1] - self.mouse_old[1]

            if self.mouse_raw[0] >= self.screen_x-1:   # if mouse hits screen edge
                pygame.mouse.set_pos(1, self.mouse_raw[1])   # move it to opposite edge
                self.mouse_fix_x = True   # in next itteration, dont calculate that as movement
            if self.mouse_raw[0] <= 0:
                pygame.mouse.set_pos(self.screen_x-2, self.mouse_raw[1])
                self.mouse_fix_x = True
            if self.mouse_raw[1] >= self.screen_y-1:
                pygame.mouse.set_pos(self.mouse_raw[0], 1)
                self.mouse_fix_y = True
            if self.mouse_raw[1] <= 0:
                pygame.mouse.set_pos(self.mouse_raw[0], self.screen_y-2)
                self.mouse_fix_y = True
            self.mouse_old = self.mouse

        # background lines grid
        if self.grid_mode:
            if self.grid_mode == 1:   # grid mode: home
                origin = self.screen_coords([0, 0])
            elif self.grid_mode == 2:      # grid mode: selected body
                origin = self.screen_coords(self.v_pos[self.iteration])
            else:
                origin = self.screen_coords([0, 0])
            graphics.draw_grid(screen, origin, self.zoom)

        # draw reference
        graphics.draw_circle_fill(screen, rgb.gray2, self.screen_coords((0, 0)), REF_RADIUS * self.zoom)

        # BODY
        # curve lines
        curve = self.screen_coords_array(self.b_curve)
        # previous body coi
        coi_screen = self.b_coi * self.zoom
        radius_screen = b_radius * self.zoom
        if b_radius < self.b_coi:   # determine text position
            b_note_offset = (coi_screen + 5) * math.sin(np.pi / 4)
        elif radius_screen >= 5:
            b_note_offset = (b_radius + 5) * math.sin(np.pi / 4)
        else:
            b_note_offset = 11 * math.sin(np.pi / 4)
        if self.iteration:
            for i, prev_pos in enumerate(self.b_pos[:self.iteration]):
                prev_body_pos = self.screen_coords(prev_pos)
                opacity = int(60 + 180/self.iteration*(i+1))
                gray = int(15 + 25/self.iteration*(i+1))
                text_color = (20, 20, opacity)
                coi_color = (gray, gray, gray)
                text_pos = (prev_body_pos[0] + b_note_offset, prev_body_pos[1] - b_note_offset)
                graphics.text(screen, text_color, self.fontsm, str(i), text_pos, True, rgb.black)
                note_pos = (text_pos[0] + 5 + len(str(i))*3, text_pos[1])
                if self.iteration_types[i] == 1:
                    graphics.text(screen, (20, 20, opacity), self.fontsm, "S1", note_pos, True, rgb.black)
                elif self.iteration_types[i] == 2:
                    graphics.text(screen, (opacity, 20, 20), self.fontsm, "S2", note_pos, True, rgb.black)
                elif self.iteration_types[i] == 3:
                    graphics.text(screen, (20, opacity, 20), self.fontsm, "B ", note_pos, True, rgb.black)
                graphics.draw_circle(screen, coi_color, prev_body_pos, coi_screen, 1)
        body_pos = self.screen_coords(self.b_pos[self.iteration])
        graphics.draw_lines(screen, rgb.blue, curve, 2)
        # circle of influence
        text_pos = (body_pos[0] + b_note_offset, body_pos[1] - b_note_offset)
        graphics.text(screen, rgb.blue, self.fontsm, str(self.iteration), text_pos, True, rgb.black)
        note_pos = (text_pos[0] + 5 + len(str(self.iteration))*3, text_pos[1])
        if self.iteration_types[self.iteration] == 1:
            graphics.text(screen, rgb.blue, self.fontsm, "S1", note_pos, True, rgb.black)
        elif self.iteration_types[self.iteration] == 2:
            graphics.text(screen, rgb.red, self.fontsm, "S2", note_pos, True, rgb.black)
        elif self.iteration_types[self.iteration] == 3:
            graphics.text(screen, rgb.green, self.fontsm, "B ", note_pos, True, rgb.black)
        if b_radius < self.b_coi:
            graphics.draw_circle(screen, rgb.gray2, body_pos, coi_screen, 1)
        # body
        if radius_screen >= 5:
            graphics.draw_circle_fill(screen, rgb.blue, body_pos, radius_screen)
        else:
            graphics.draw_circle_fill(screen, rgb.gray1, body_pos, 6)
            graphics.draw_circle_fill(screen, rgb.gray2, body_pos, 5)
            graphics.draw_circle_fill(screen, rgb.blue, body_pos, 4)

        # VESSEL
        # curve lines
        curve = self.screen_coords_array(self.v_curve)
        graphics.draw_lines(screen, rgb.cyan, curve, 2)
        # current, initial and end vessel positions
        vessel_pos = self.screen_coords(self.v_pos[self.iteration])
        vessel_init_pos = self.screen_coords(self.v_init_pos)
        vessel_end_pos = self.screen_coords(self.v_end_pos)
        graphics.draw_circle_fill(screen, rgb.purple, vessel_init_pos, v_radius)
        graphics.draw_circle_fill(screen, rgb.green, vessel_end_pos, v_radius)
        # previous vessel positions
        if self.iteration:
            for i, prev_pos in enumerate(self.v_pos[:self.iteration]):
                prev_vessel_pos = self.screen_coords(prev_pos)
                opacity = int(60 + 180/self.iteration*(i+1))
                color = (opacity, 20, 20)
                text_pos = (prev_vessel_pos[0] + v_note_offset, prev_vessel_pos[1] - v_note_offset)
                graphics.text(screen, color, self.fontsm, str(i), text_pos, True, rgb.black)
                note_pos = (text_pos[0] + 5 + len(str(i))*3, text_pos[1])
                if self.iteration_types[i] == 1:
                    graphics.text(screen, (20, 20, opacity), self.fontsm, "S1", note_pos, True, rgb.black)
                elif self.iteration_types[i] == 2:
                    graphics.text(screen, (opacity, 20, 20), self.fontsm, "S2", note_pos, True, rgb.black)
                elif self.iteration_types[i] == 3:
                    graphics.text(screen, (20, opacity, 20), self.fontsm, "B ", note_pos, True, rgb.black)
                graphics.text(screen, color, self.fontsm, str(i), text_pos, True, rgb.black)
                graphics.draw_circle_fill(screen, color, prev_vessel_pos, v_radius-1)
        text_pos = (vessel_pos[0] + v_note_offset, vessel_pos[1] - v_note_offset)
        graphics.text(screen, rgb.red, self.fontsm, str(self.iteration), text_pos, True, rgb.black)
        note_pos = (text_pos[0] + 5 + len(str(self.iteration))*3, text_pos[1])
        if self.iteration_types[self.iteration] == 1:
            graphics.text(screen, rgb.blue, self.fontsm, "S1", note_pos, True, rgb.black)
        elif self.iteration_types[self.iteration] == 2:
            graphics.text(screen, rgb.red, self.fontsm, "S2", note_pos, True, rgb.black)
        elif self.iteration_types[self.iteration] == 3:
            graphics.text(screen, rgb.green, self.fontsm, "B ", note_pos, True, rgb.black)
        graphics.draw_circle_fill(screen, rgb.red, vessel_pos, v_radius)
        # orbit-coi intersections
        for intersection in self.intersections_pos:
            graphics.draw_circle_fill(screen, rgb.gray, self.screen_coords(intersection), 2)

        # texts
        if self.show_log:
            graphics.text(screen, rgb.gray1, self.fontmd, self.system_text, (3, 2))
            graphics.text(screen, rgb.gray1, self.fontmd, self.data_text, (3, 65))
            graphics.text(screen, rgb.gray1, self.fontmd, self.end_text, (3, 370))
            graphics.text(screen, rgb.gray1, self.fontmd, self.probe_text, (3, 508))
            graphics.text(screen, rgb.gray1, self.fontmd, self.search_text, (3, 574))
            iteration_text = f"Iteration: {self.iteration}"
            graphics.text(screen, rgb.gray, self.fontmd, iteration_text, (self.screen_x/2, 9), center=True)
            if self.opposed:
                graphics.text(screen, rgb.red1, self.fontmd, "OPPOSED", (self.screen_x/2 - 80, 9), center=True)
                if self.iteration_types[self.iteration] == 1:
                    graphics.text(screen, rgb.blue1, self.fontmd, "FIRST STAGE", (self.screen_x/2 + 95, 9), center=True)
                    color2 = rgb.blue4
                elif self.iteration_types[self.iteration] == 2:
                    graphics.text(screen, rgb.red1, self.fontmd, "SECOND STAGE", (self.screen_x/2 + 95, 9), center=True)
                    color2 = rgb.red4
                elif self.iteration_types[self.iteration] == 3:
                    graphics.text(screen, rgb.green1, self.fontmd, "BACKING", (self.screen_x/2 + 95, 9), center=True)
                    color2 = rgb.green4
                else:
                    color2 = rgb.gray1
                if self.iteration > 0:
                    if self.iteration_types[self.iteration-1] == 1:
                        color1 = rgb.blue4
                    elif self.iteration_types[self.iteration-1] == 2:
                        color1 = rgb.red4
                    elif self.iteration_types[self.iteration-1] == 3:
                        color1 = rgb.green4
                    else:
                        color1 = rgb.gray1
                if self.iteration < len(self.iteration_texts) - 1:
                    if self.iteration_types[self.iteration+1] == 1:
                        color3 = rgb.blue4
                    elif self.iteration_types[self.iteration+1] == 2:
                        color3 = rgb.red4
                    elif self.iteration_types[self.iteration+1] == 3:
                        color3 = rgb.green4
                    else:
                        color3 = rgb.gray1
            else:
                color1 = rgb.gray1
                color2 = rgb.gray
                color3 = rgb.gray1
            if self.iteration > 0:
                graphics.text(screen, color1, self.fontmd, self.iteration_texts[self.iteration-1], (self.screen_x - 310, 2))
            graphics.text(screen, color2, self.fontmd, self.iteration_texts[self.iteration], (self.screen_x - 310, 260))
            if self.iteration < len(self.iteration_texts) - 1:
                graphics.text(screen, color3, self.fontmd, self.iteration_texts[self.iteration+1], (self.screen_x - 310, 520))
        graphics.timed_text(screen)

        if self.screenshot:
            if not os.path.exists("Screenshots"):
                os.mkdir("Screenshots")
            date = time.strftime("%Y-%m-%d %H-%M-%S")
            screenshot_path = f"Screenshots/Screenshot from {date}.png"
            pygame.image.save(screen, screenshot_path)
            if not self.disable_ui:
                graphics.timed_text_init(
                    rgb.gray0, self.fontmd,
                    "Screenshot saved at: " + screenshot_path,
                    (self.screen_x/2, self.screen_y-70), 2, True,
                )
            self.screenshot = False



def main(args):
    """Main runner function"""
    # parse arguments
    fullscreen = args.fullscreen
    display = args.display
    file_path = args.path
    if not (file_path.endswith(".ini") or file_path.endswith(".txt") or file_path.endswith(".log")):
        print("Invalid file format.")
        sys.exit()

    pygame.display.init()
    pygame.font.init()
    pygame.display.set_caption("Volatile Sspace - Enter COI Debugger")
    pygame.display.set_icon(pygame.image.load("img/icon.png"))
    avail_res = pygame.display.get_desktop_sizes()
    (screen_x, screen_y) = avail_res[0]   # use highest resolution
    if fullscreen is True:
        screen = pygame.display.set_mode((screen_x, screen_y), pygame.FULLSCREEN, vsync=VSYNC, display=display)
    else:
        screen = pygame.display.set_mode((screen_x, screen_y), vsync=VSYNC)
    pygame.display.init()
    global graphics
    graphics = graphics.Graphics()
    clock = pygame.time.Clock()
    # userevent is called every 1/60 of second (rounded to 17ms)
    pygame.time.set_timer(pygame.USEREVENT, int(round(1000/60)))
    debugger = Debugger()

    # handle files
    if file_path.endswith(".ini"):
        log_path = simulate(file_path)
        debugger.read_log(log_path, file_path)
    elif file_path.endswith(".txt") or file_path.endswith(".log"):
        debugger.read_log(file_path, None)

    fps = 60
    run = True
    while run:
        for event in pygame.event.get():
            if event.type == pygame.WINDOWFOCUSGAINED:
                fps = 60
            if event.type == pygame.WINDOWFOCUSLOST:
                fps = 3
            debugger.input_keys(event)
            debugger.input_mouse(event)
            if event.type == pygame.QUIT or (event.type == pygame.KEYDOWN and event.key in (pygame.K_ESCAPE, pygame.K_q)):
                pygame.quit()
                sys.exit()
        debugger.graphics(screen)
        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()


def argparser():
    """Setup argument parser for CLI"""
    parser = argparse.ArgumentParser(
        prog="enter-coi-debugger",
        description="Graphical debugger for enter-COI prediction numerical algorithm. See documentation for more info.",
        )
    parser.add_argument(
        "path",
        help="path to log file or ini file containing input data.",
        )
    parser.add_argument(
        "-f",
        "--fullscreen",
        action="store_true",
        help="run in fullscreen mode",
        )
    parser.add_argument(
        "-d",
        "--display",
        type=int,
        default=0,
        help="display to open fullscreen window at",
        )
    parser.add_argument(
        "-v",
        "--version",
        action="version",
        version=f"%(prog)s {VERSION}",
        )
    return parser.parse_args()


if __name__ == "__main__":
    args = argparser()
    main(args)
