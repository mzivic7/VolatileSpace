import math
import os
import sys
import time

import numpy as np
import pygame

from volatilespace import format_time, metric, peripherals, textinput
from volatilespace.graphics import bg_stars, graphics, rgb
from volatilespace.physics import convert, phys_body, phys_vessel
from volatilespace.physics.phys_shared import point_between

physics_body = phys_body.Physics()
physics_vessel = phys_vessel.Physics()
graphics = graphics.Graphics()
bg_stars = bg_stars.BgStars()
textinput = textinput.Textinput()

buttons_pause_menu = [
    "Resume",
    "Save game",
    "Load game",
    "Settings",
    "Quit without saving",
    "Save and Quit",
]
buttons_save = ["Cancel", "Save", "New save"]
buttons_load = ["Cancel", "Load"]
buttons_new_game = ["Cancel", "Create"]
body_types = ["Dwarf planet", "Solid planet", "Gas planet", "Star", "Black Hole"]
text_data_orb = [
    "Target: ",
    "Ref body: ",
    "Periapsis: ",
    "Apoapsis: ",
    "Eccentricity: ",
    "Argument of Pe: ",
    "Mean anomaly: ",
    "True anomaly: ",
    "Direction: ",
    "Distance: ",
    "Orbital Period: ",
    "Orbital Speed: ",
    "Horizontal Speed: ",
    "Vertical Speed: ",
]
text_data_body = ["Target: ", "Type: ", "Mass: ", "Density: ", "Radius: ", "COI altitude: "]
text_data_planet = [
    "(Rotation period): ",
    "Color: ",
    "Atmosphere height: ",
    "Surface gravity: ",
]
text_data_star = [
    "Effective temp: ",
    "Luminosity: ",
    "Stellar class: ",
]
text_data_bh = ["Schwarzschild radius: "]
text_follow_mode = ["Disabled", "Active vessel", "Orbited body"]
text_grid_mode = ["Disabled", "Global", "Active vessel", "Orbited body"]


class Game():
    """Main game class"""
    def __init__(self):
        self.state = 3
        self.sim_name = "Unknown"
        self.screen_mode = False
        self.screenshot = False

        # menu related
        self.ask = None
        self.pause_menu = False
        self.disable_input = False
        self.allow_keys = False   # allow keys when disable_input is True
        self.disable_ui = False
        self.disable_labels = False
        self.menu = None
        self.right_menu = None
        self.new_game = False
        self.text = ""
        self.click = False
        self.vessel_potential_target = None
        self.first_click = None
        self.click_timer = 0
        self.scroll = 0
        self.scroll_sensitivity = 10
        self.scrollbar_drag = False
        self.selected_item = 0
        self.fontbt = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 22)   # button text font
        self.fontmd = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 16)   # medium text font
        self.fontsm = pygame.font.Font("fonts/LiberationSans-Regular.ttf", 10)   # small text font
        self.btn_w = 250   # button width
        self.btn_w_h = 200   # for horizontal placement
        self.btn_w_l = 500   # for lists
        self.btn_w_h_3 = (self.btn_w_l + 16)/3   # fits 3 btn in width of list button
        self.btn_w_h_2 = (self.btn_w_l + 26)/2  # fits 2 btn in width of list button
        self.txt_y_margin = 8  # empty space between text and button edge
        self.btn_h = self.fontbt.get_height() + self.txt_y_margin * 2   # button height from font height
        self.btn_s = 36   # small square button
        self.btn_sm = 22   # very small square button
        self.space = 10   # space between buttons
        self.file_path = ""   # path to currently active file
        self.selected_path = ""
        self.input_value = None   # which value is being text-inputed
        self.new_value_raw = ""
        self.edited_orbit = False   # if orbit is edited, on first click call kepler_inverse, but don't on next clicks
        self.hold_key = None
        self.gen_game_list()
        self.reload_settings()
        graphics.antial = self.antial

        # simulation related
        self.ptps = 58.823   # divisor to convert simulation time to real time (it is not 60 because userevent timer is rounded to 17ms)
        self.zoom = 0.15
        self.select_sensitivity = 5
        self.drag_sensitivity = 0.02   # when inserting body
        self.warp_range = [1, 2, 3, 4, 5, 10, 50, 100, 1000]
        self.warp_index = 0
        self.warp = self.warp_range[self.warp_index]
        self.warp_mem = None
        self.warp_phys_active = True
        self.warp_phys_range = [1, 2, 4, 8]
        self.warp_phys_index = 0
        self.warp_phys = self.warp_range[self.warp_index]
        self.warp_phys_mem = None
        self.disable_warp_changing = False
        self.vessel_crossing = None
        self.sim_time = 0
        self.pause = False
        self.move = False
        self.target = None   # 0-body, 1-vessel
        self.target_type = None   # vessel/body
        self.active_vessel = None
        self.follow = 1   # 0-disabled, 1-active vessel, 2-orbited body
        self.mouse = [0, 0]   # in simulation
        self.mouse_raw = [0, 0]   # on screen
        self.mouse_raw_old = [0, 0]
        self.offset_x = self.screen_x / 2
        self.offset_y = self.screen_y / 2
        self.follow_offset_x = self.screen_x / 2
        self.follow_offset_y = self.screen_y / 2
        self.mouse_fix_x = False   # fix mouse movement when jumping off screen edge
        self.mouse_fix_y = False
        self.zoom_step = 0.05
        self.orbit_data_menu = []   # data for right_menu when body is selected
        self.pos = np.array([])
        self.ma = np.array([])
        self.curves = np.array([])
        self.v_pos = np.array([])
        self.v_ma = np.array([])
        self.v_curves = np.array([])
        self.v_rot_angle = np.array([])
        self.v_rot_dir = 0
        self.visible_bodies = np.array([])
        self.visible_coi = np.array([])
        self.visible_body_orbits = np.array([])
        self.visible_vessel_orbits = np.array([])
        self.visible_vessels = np.array([])
        self.change_vessel = None

        # DEBUG
        self.physics_debug_time = 1
        self.debug_timer = 0
        self.physics_debug_time_sum = 0
        self.physics_debug_percent = 0

        self.offset_old = np.array([self.offset_x, self.offset_y])
        self.grid_mode = 0   # 0 - global, 1 - selected body, 2 - parent

        # icons
        menu_img = pygame.image.load("images/menu.png").convert_alpha()
        body_list_img = pygame.image.load("images/body_list.png").convert_alpha()
        orbit_sel_img = pygame.image.load("images/orbit_select.png").convert_alpha()
        body_img = pygame.image.load("images/body_select.png").convert_alpha()
        self.ui_imgs = [menu_img, body_list_img, orbit_sel_img, body_img]
        follow_none_img = pygame.image.load("images/follow_none.png").convert_alpha()
        follow_vessel_img = pygame.image.load("images/follow_vessel.png").convert_alpha()
        follow_ref_img = pygame.image.load("images/follow_ref.png").convert_alpha()
        self.top_ui_img_follow = [follow_none_img, follow_vessel_img, follow_ref_img]
        warp_0_img = pygame.image.load("images/warp_0.png").convert_alpha()
        warp_0_img = graphics.fill(warp_0_img, rgb.red)
        warp_1_img = pygame.image.load("images/warp_1.png").convert_alpha()
        warp_2_img = pygame.image.load("images/warp_2.png").convert_alpha()
        warp_3_img = pygame.image.load("images/warp_3.png").convert_alpha()
        self.top_ui_img_warp = [warp_0_img, warp_1_img, warp_2_img, warp_3_img]
        self.top_ui_img_warp_phys = [
            warp_0_img,
            graphics.fill(warp_1_img, rgb.orange),
            graphics.fill(warp_2_img, rgb.orange),
            graphics.fill(warp_3_img, rgb.orange),
        ]
        grid_global_img = pygame.image.load("images/grid_global.png").convert_alpha()
        grid_vessel_img = pygame.image.load("images/grid_vessel.png").convert_alpha()
        grid_ref_img = pygame.image.load("images/grid_ref.png").convert_alpha()
        grid_disabled_img = graphics.fill(grid_global_img, rgb.gray0)
        self.top_ui_img_grid = [grid_disabled_img, grid_global_img, grid_vessel_img, grid_ref_img]
        self.top_ui_imgs = [warp_1_img, follow_vessel_img, grid_disabled_img]
        body_dwarf = pygame.image.load("images/moon.png").convert_alpha()
        body_planet_solid = pygame.image.load("images/planet_solid.png").convert_alpha()
        body_planet_gas = pygame.image.load("images/planet_gas.png").convert_alpha()
        body_star = pygame.image.load("images/star.png").convert_alpha()
        body_bh = pygame.image.load("images/bh.png").convert_alpha()
        self.body_imgs = [body_dwarf, body_planet_solid, body_planet_gas, body_star, body_bh]
        self.vessel_img = graphics.fill(pygame.image.load_sized_svg("images/vessel.svg", (24, 24)), rgb.gray).convert_alpha()
        self.target_img = pygame.image.load("images/target.png").convert_alpha()
        self.impact_img = pygame.image.load("images/impact.png").convert_alpha()
        orb_leave_img = pygame.image.load("images/orb_leave.png").convert_alpha()
        self.orb_leave_img_cyan = graphics.fill(orb_leave_img, rgb.cyan)
        self.orb_leave_img_gray = graphics.fill(orb_leave_img, rgb.gray)
        orb_enter_img = pygame.image.load("images/orb_enter.png").convert_alpha()
        self.orb_enter_img_cyan = graphics.fill(orb_enter_img, rgb.cyan)
        self.orb_enter_img_gray = graphics.fill(orb_enter_img, rgb.gray)

        bg_stars.set_screen()
        graphics.set_screen()


    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.screen_dim = np.array([self.screen_x, self.screen_y])
        self.ask_x = self.screen_x/2 - (2*self.btn_w_h + self.space)/2
        self.ask_y = self.screen_y/2 + self.space
        self.pause_x = self.screen_x/2 - self.btn_w/2
        self.pause_y = self.screen_y/2 - (len(buttons_pause_menu) * self.btn_h + (len(buttons_pause_menu)-1) * self.space)/2
        self.pause_max_y = self.btn_h*len(buttons_pause_menu) + self.space*(len(buttons_pause_menu)+1)
        self.games_x = self.screen_x/2 - self.btn_w_l/2
        self.games_max_y = self.screen_y - 200
        self.list_limit = self.games_max_y - self.btn_h - self.space
        self.games_y = (self.screen_y - self.games_max_y)/2
        self.games_x_ui = self.games_x - self.space
        self.games_y_ui = self.games_y + self.list_limit + self.space
        self.game_list_size = len(self.games) * self.btn_h + len(self.games) * self.space
        self.right_menu_x = self.screen_x - 300
        self.r_menu_limit = self.screen_y - 38 - self.space
        self.r_menu_x_btn = self.right_menu_x + self.space
        bg_stars.set_screen()
        graphics.set_screen()


    def reload_settings(self):
        """Reload all settings for editor and graphics, should be run every time editor is entered"""
        self.fullscreen = peripherals.load_settings("graphics", "fullscreen")
        avail_res = pygame.display.list_modes()
        self.screen_x, self.screen_y = pygame.display.get_surface().get_size()
        self.screen_dim = np.array((self.screen_x, self.screen_y))
        try:
            self.selected_res = avail_res.index((self.screen_x, self.screen_y))
        except Exception:   # fail-safe repair if resolution is invalid
            self.selected_res = 0   # use maximum resolution
            peripherals.save_settings("graphics", "resolution", list(avail_res[0]))
            if self.fullscreen:
                pygame.display.set_mode((avail_res[0]), pygame.FULLSCREEN)
            else:
                pygame.display.set_mode((avail_res[0]))
        self.antial = peripherals.load_settings("graphics", "antialiasing")
        self.mouse_warp = peripherals.load_settings("graphics", "mouse_warp")
        self.bg_stars_enable = peripherals.load_settings("background", "stars")
        bg_stars.reload_settings()
        graphics.reload_settings()
        physics_body.reload_settings()
        physics_vessel.reload_settings()
        self.set_screen()   # resolution may have been changed
        bg_stars.set_screen()
        graphics.set_screen()
        self.keys = peripherals.load_keybindings()
        self.right_menu = None
        self.autosave_event = pygame.USEREVENT + 1
        autosave_time = int(peripherals.load_settings("game", "autosave_time")) * 60 * 1000   # min to ms
        pygame.time.set_timer(self.autosave_event, autosave_time)


    def gen_game_list(self):
        """Generate list of games and select currently active file"""
        self.games = peripherals.gen_game_list()
        self.game_list_size = len(self.games) * self.btn_h + len(self.games) * self.space
        if len(self.games) != 0:
            self.selected_path = "Saves/" + self.games[self.selected_item, 0]

        # limit text size
        for num, text in enumerate(self.games[:, 1]):
            new_text = graphics.limit_text(text, self.fontbt, self.btn_w_l)
            if new_text != text:
                self.games[num, 1] = new_text

        # find selected item based on currently active file
        selected_item = np.where(self.games[:, 0] == self.file_path.strip("Saves/"))[0]
        if len(selected_item) == 0:
            self.selected_item = 0
        else:
            self.selected_item = selected_item[0]
            self.selected_path = "Saves/" + self.games[self.selected_item, 0]


    def load_system(self, system):
        """Load system from file and convert to kepler orbit if needed"""
        game_data, self.sim_conf, body_data, body_orb_data, vessel_data, vessel_orb_data = peripherals.load_file(system)
        self.sim_name = game_data["name"]
        self.sim_time = game_data["time"]
        self.vessel_scale = self.sim_conf["vessel_scale"]
        self.names = body_data["name"]
        self.mass = body_data["mass"]
        self.density = body_data["den"]
        self.color = body_data["color"]
        if not body_orb_data["kepler"]:   # convert to keplerian model
            body_orb_data = convert.to_kepler(self.mass, body_orb_data, self.sim_conf["gc"], self.sim_conf["coi_coef"])
            os.remove(system)
            peripherals.save_file(
                system, game_data, self.sim_conf,
                body_data, body_orb_data,
                vessel_data, vessel_orb_data,
            )

        self.file_path = system   # this path will be used for load/save
        self.pause_menu = 0
        self.disable_input = False
        self.disable_ui = False
        self.disable_labels = False
        self.gen_game_list()
        self.selected_item = 0
        self.set_pause(False)
        self.warp_index = 0
        self.warp = 1
        self.warp_mem = None
        self.warp_phys_active = False
        self.warp_phys_index = 0
        self.warp_phys = 1
        self.warp_phys_mem = None
        self.disable_warp_changing = False
        self.set_warp_ui(True)
        self.follow = 1
        self.grid_mode = 0
        self.follow_offset_x = self.screen_x / 2
        self.follow_offset_y = self.screen_y / 2
        self.top_ui_imgs = [self.top_ui_img_warp[1], self.top_ui_img_follow[1], self.top_ui_img_grid[0]]

        # userevent may not be run in first iteration, but this values are needed in graphics section
        physics_body.load(self.sim_conf, body_data, body_orb_data)

        body_data, body_orb_data, self.pos, self.ma, ea, self.curves = physics_body.initial(self.warp)
        self.unpack_body(body_data, body_orb_data)

        physics_vessel.load(self.sim_conf, body_data, body_orb_data, vessel_data, vessel_orb_data)
        vessel_orb_data, self.v_pos, self.v_ma, self.v_curves = physics_vessel.initial(self.warp, self.pos, self.ma, ea)
        self.unpack_vessel(vessel_data, vessel_orb_data)

        self.active_vessel = game_data["vessel"]
        if self.active_vessel is not None and self.active_vessel < len(self.v_ref):
            self.target = self.v_ref[self.active_vessel]
            self.focus_point(self.v_pos[self.active_vessel], 0.5)
        else:
            self.active_vessel = None
            self.target = None
            self.focus_point([0, 0], 0.5)
        self.target_type = 0



    def focus_point(self, pos, zoom=None):
        """Calculate offset and zoom, used to focus on specific coordinates"""
        if zoom:
            self.zoom = zoom
        self.offset_x = - pos[0] + self.screen_x / 2   # follow selected body
        self.offset_y = - pos[1] + self.screen_y / 2
        self.zoom_x = (self.screen_x / 2) - (self.screen_x / (self.zoom * 2))   # zoom translation to center
        self.zoom_y = (self.screen_y / 2) - (self.screen_y / (self.zoom * 2))
        self.follow_offset_x = self.screen_x / 2
        self.follow_offset_y = self.screen_y / 2


    def screen_coords(self, coords_in_sim):
        """Convert from sim coords to screen coords. Add zoom, view move, and move origin from up-left to bottom-left"""
        # correction for zoom, screen movement offset
        x_on_screen = (coords_in_sim[0] + self.offset_x - self.zoom_x) * self.zoom
        y_on_screen = (coords_in_sim[1] + self.offset_y - self.zoom_y) * self.zoom
        # move origin from up-left to bottom-left
        y_on_screen = self.screen_y - y_on_screen
        return np.array([x_on_screen, y_on_screen])


    def screen_coords_array(self, coords_in_sim):
        """Convert from sim coords to screen coords, for array with shape: [points, axes]. Add zoom, view move, and move origin from up-left to bottom-left"""
        # correction for zoom, screen movement offset
        x_on_screen = (coords_in_sim[:, 0] + self.offset_x - self.zoom_x) * self.zoom
        y_on_screen = (coords_in_sim[:, 1] + self.offset_y - self.zoom_y) * self.zoom
        # move origin from up-left to bottom-left
        y_on_screen = self.screen_y - y_on_screen
        return np.column_stack([x_on_screen, y_on_screen])


    def sim_coords(self, coords_on_screen):
        """Converts from screen coords to sim coords. Adds zoom, view move, and moves origin from bottom-left to up-left"""
        x_in_sim = coords_on_screen[0] / self.zoom - self.offset_x + self.zoom_x
        y_in_sim = -(coords_on_screen[1] - self.screen_y) / self.zoom - self.offset_y + self.zoom_y   # move origin from bottom-left to up-lef
        return [x_in_sim, y_in_sim]


    def unpack_body(self, body_data, body_orb):
        """Unpack values from dict and stores them in class variables"""
        # body data
        self.names = body_data["name"]
        self.types = body_data["type"]
        self.mass = body_data["mass"]
        self.density = body_data["den"]
        self.temp = body_data["temp"]
        self.luminosity = body_data["lum"]
        self.stellar_class = body_data["class"]
        self.base_color = body_data["color_b"]
        self.color = body_data["color"]
        self.atm_h = body_data["atm_h"]
        self.atm_data = [body_data["atm_pres0"], body_data["atm_scale_h"], body_data["atm_den0"]]
        self.surf_grav = body_data["surf_grav"]
        self.radius = body_data["radius"]
        self.rad_sc = body_data["rad_sc"]
        # orbit data
        self.a = body_orb["a"]
        self.coi = body_orb["coi"]
        self.ref = body_orb["ref"]
        self.ecc = body_orb["ecc"]
        self.pe_d = body_orb["pe_d"]
        self.ap_d = body_orb["ap_d"]
        self.pea = body_orb["pea"]
        self.dr = body_orb["dir"]
        self.period = body_orb["per"]


    def unpack_vessel(self, vessel_data, vessel_orb):
        """Unpack vessel data from vessel dict and update it in this class"""
        # body data
        self.v_names = vessel_data["name"]
        self.v_mass = vessel_data["mass"]
        self.v_rot_angle = vessel_data["rot_angle"]
        self.v_rot_acc = vessel_data["rot_acc"]
        self.v_sprite = vessel_data["sprite"]
        # orbit data
        self.v_a = vessel_orb["a"]
        self.v_ref = vessel_orb["ref"]
        self.v_ecc = vessel_orb["ecc"]
        self.v_pe_d = vessel_orb["pe_d"]
        self.v_ap_d = vessel_orb["ap_d"]
        self.v_pea = vessel_orb["pea"]
        self.v_dr = vessel_orb["dir"]
        self.v_period = vessel_orb["per"]


    def update_vessel(self, vessel, vessel_data, vessel_orb):
        """Update vessel data after its orbit has been changed"""
        # body data
        self.v_names[vessel] = vessel_data[0]
        # orbit data
        self.v_a[vessel] = vessel_orb[0]
        if self.v_ref[vessel] != vessel_orb[1] and self.active_vessel == vessel and self.follow != 0:
            self.follow = 1   # when crossing coi, change focus back to vessel
        self.v_ref[vessel] = vessel_orb[1]
        self.v_ecc[vessel] = vessel_orb[2]
        self.v_pe_d[vessel] = vessel_orb[3]
        self.v_ap_d[vessel] = vessel_orb[4]
        self.v_pea[vessel] = vessel_orb[5]
        self.v_dr[vessel] = vessel_orb[6]
        self.v_period[vessel] = vessel_orb[7]
        # change bg_stars offset
        if self.bg_stars_enable and self.follow and self.active_vessel == vessel:
            parent_pos = self.pos[self.v_ref[self.active_vessel]]
            self.offset_old = np.array([self.offset_x, self.offset_y]) + parent_pos


    def load(self):
        """Load system from 'load' dialog"""
        if os.path.exists(self.selected_path):
            self.load_system(self.selected_path)
            self.file_path = self.selected_path
            graphics.timed_text_init(
                rgb.gray0, self.fontmd,
                "Game loaded successfully",
                (self.screen_x/2, self.screen_y-70), 2, True,
            )


    def save(self, path, name=None, silent=False):
        """Save game to file, if name is None, name is not changed"""
        date = time.strftime("%d.%m.%Y %H:%M")
        body_data = {
            "name": self.names,
            "mass": self.mass,
            "den": self.density,
            "color": self.base_color,
            "atm_pres0": self.atm_data[0],
            "atm_scale_h": self.atm_data[1],
            "atm_den0": self.atm_data[2],
        }
        body_orb_data = {"a": self.a, "ecc": self.ecc, "pe_arg": self.pea, "ma": self.ma, "ref": self.ref, "dir": self.dr}
        vessel_data = {
            "name": self.v_names,
            "mass": self.v_mass,
            "rot_angle": self.v_rot_angle,
            "rot_acc": self.v_rot_acc,
            "sprite": self.v_sprite,
        }
        vessel_orb_data = {"a": self.v_a, "ecc": self.v_ecc, "pe_arg": self.v_pea, "ma": self.v_ma, "ref": self.v_ref, "dir": self.v_dr}
        game_data = {"name": name, "date": date, "time": self.sim_time, "vessel": self.active_vessel}
        peripherals.save_file(
            path,
            game_data,
            self.sim_conf,
            body_data,
            body_orb_data,
            vessel_data,
            vessel_orb_data)
        if not silent:
            graphics.timed_text_init(
                rgb.gray0, self.fontmd,
                "Game saved successfully",
                (self.screen_x/2, self.screen_y-70), 2, True,
            )


    def quicksave(self):
        """Save game to quicksave file"""
        self.save("Saves/quicksave.ini", "Quicksave - " + self.sim_name, True)
        graphics.timed_text_init(
            rgb.gray0, self.fontmd,
            "Quicksave...",
            (self.screen_x/2, self.screen_y-70), 2, True,
        )


    def autosave(self, e):
        """Automatically save current game to autosave.ini at predefined interval"""
        if e.type == self.autosave_event:
            self.save("Saves/autosave.ini", "Autosave - " + self.sim_name, True)
            graphics.timed_text_init(
                rgb.gray1, self.fontmd,
                "Autosave...",
                (self.screen_x/2, self.screen_y-70), 2, True,
            )


    def set_pause(self, do=None):
        """Pause game, set warp to x1 and update top UI"""
        if do is not None:
            self.pause = do
        else:
            self.pause = not self.pause
        self.warp_index = 0
        self.warp = self.warp_range[self.warp_index]
        self.top_ui_imgs[0] = self.top_ui_img_warp[int(not self.pause)]


    def set_warp_ui(self, silent=False):
        """Set warp UI in top panel and handle notifications"""
        if self.warp_phys_active:
            if self.warp_phys_index < 2:
                ui_warp_index = 1
            elif self.warp_phys_index == 2:
                ui_warp_index = 2
            else:
                ui_warp_index = 3
            self.top_ui_imgs[0] = self.top_ui_img_warp_phys[ui_warp_index]
            if not silent:
                if self.disable_warp_changing:
                    graphics.timed_text_init(
                        rgb.gray0, self.fontmd,
                        "Time warp is disabled due to vessel crossing COI.",
                        (self.screen_x/2, self.screen_y-70), 1.5, True,
                    )
                else:
                    graphics.timed_text_init(
                        rgb.orange, self.fontmd,
                        "Physical warp: x" + str(self.warp_phys),
                        (self.screen_x/2, self.screen_y-70), 1, True,
                    )
        else:
            if self.warp_index < 3:
                ui_warp_index = 1
            elif self.warp_index < 6:
                ui_warp_index = 2
            else:
                ui_warp_index = 3
            self.top_ui_imgs[0] = self.top_ui_img_warp[ui_warp_index]
            if not silent:
                if self.disable_warp_changing:
                    graphics.timed_text_init(
                        rgb.gray0, self.fontmd,
                        "Time warp is disabled due to vessel crossing COI.",
                        (self.screen_x/2, self.screen_y-70), 1.5, True,
                    )
                else:
                    graphics.timed_text_init(
                        rgb.gray0, self.fontmd,
                        "Time warp: x" + str(self.warp),
                        (self.screen_x/2, self.screen_y-70), 1, True,
                    )


    def input_keys(self, e):
        """Simulation and menu keys"""
        if self.state != 2:   # when returning to editor menu
            self.state = 2

        # new game menu
        if self.new_game:
            self.text = textinput.input(e)
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    self.new_game = False
                    self.ask = None
                elif e.key == pygame.K_RETURN:
                    path = peripherals.new_game(self.text, time.strftime("%d.%m.%Y %H:%M"))
                    self.save(path, name=self.text)
                    self.gen_game_list()
                    self.new_game = False
                    self.ask = None

        # save and load menu
        elif self.menu == 0 or self.menu == 1:
            if e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    if self.scrollbar_drag:
                        self.scrollbar_drag = False
                    elif self.ask:
                        self.ask = None
                    else:
                        self.menu = None
                        self.pause_menu = True
                if e.key == pygame.K_RETURN:
                    if self.ask:
                        if self.ask == "load":
                            self.load()
                        if self.ask == "save":
                            self.save(self.selected_path)
                            self.file_path = self.selected_path
                        self.menu = None
                        self.pause_menu = False
                        self.disable_input = False
                        self.ask = None
                    if self.menu == 0:
                        self.ask = "save"
                    elif self.menu == 1:
                        self.ask = "load"
                if not self.ask:
                    if e.key == pygame.K_DOWN:
                        if self.selected_item < len(self.games)-1:
                            self.selected_item += 1
                            self.selected_path = "Saves/" + self.games[self.selected_item, 0]
                    elif e.key == pygame.K_UP:
                        if self.selected_item > 0:
                            self.selected_item -= 1
                            self.selected_path = "Saves/" + self.games[self.selected_item, 0]

        # in game
        elif e.type == pygame.KEYDOWN:
            if e.key == pygame.K_ESCAPE:
                self.move = False   # disable screen movement
                if self.ask is None:
                    if self.pause_menu:
                        self.pause_menu = False
                        self.disable_input = False
                        self.set_pause(False)
                    else:
                        self.pause_menu = True
                        self.disable_input = True
                        self.set_pause(True)
                else:   # exit from ask window
                    self.ask = None
                    self.disable_input = False

            if not self.disable_input or self.allow_keys:
                if e.key == self.keys["interactive_pause"]:
                    self.set_pause()

                elif e.key == self.keys["focus_home"]:
                    self.follow = 1   # follow vessel
                    if self.active_vessel is not None:
                        pos = self.v_pos[self.active_vessel]
                    else:
                        pos = [0, 0]
                    self.focus_point(pos, self.zoom)

                elif e.key == self.keys["cycle_follow_modes"]:
                    if self.active_vessel is not None:
                        self.follow += 1   # cycle follow modes (0-disabled, 1-active vessel, 2-orbited body)
                        if self.follow > 2:
                            self.follow = 0
                        self.follow_offset_x = self.screen_x / 2
                        self.follow_offset_y = self.screen_y / 2
                        self.top_ui_imgs[1] = self.top_ui_img_follow[self.follow]
                        text = text_follow_mode[self.follow]
                        graphics.timed_text_init(
                            rgb.gray0, self.fontmd,
                            "Follow: " + text,
                            (self.screen_x/2, self.screen_y-70), 1.5, True,
                        )

                elif e.key == self.keys["cycle_grid_modes"]:
                    self.grid_mode += 1   # cycle grid modes (0-disabled, 1-global, 2-active vessel, 3-orbited body)
                    if self.grid_mode > 3:
                        self.grid_mode = 0
                    self.top_ui_imgs[2] = self.top_ui_img_grid[self.grid_mode]
                    text = text_grid_mode[self.grid_mode]
                    graphics.timed_text_init(
                        rgb.gray0, self.fontmd,
                        "Grid: " + text,
                        (self.screen_x/2, self.screen_y-70), 1.5, True,
                    )

                elif e.key == self.keys["screenshot"]:
                    self.screenshot = True

                elif e.key == self.keys["toggle_ui_visibility"]:
                    self.disable_ui = not self.disable_ui

                elif e.key == self.keys["toggle_labels_visibility"]:
                    self.disable_labels = not self.disable_labels

                elif e.key == self.keys["quicksave"]:
                    self.quicksave()

                elif e.key == self.keys["rotate_cw"]:
                    self.hold_key = self.keys["rotate_cw"]

                elif e.key == self.keys["rotate_ccw"]:
                    self.hold_key = self.keys["rotate_ccw"]

                # time warp
                if not self.pause:
                    if e.key == self.keys["decrease_time_warp"]:
                        if self.disable_warp_changing:
                            pass
                        elif self.warp_phys_active:
                            if self.warp_phys_index > 0:   # stop index from going out of range
                                self.warp_phys_index -= 1
                                self.warp_phys = self.warp_phys_range[self.warp_phys_index]
                                self.set_warp_ui()
                        elif self.warp_index > 0:
                            self.warp_index -= 1
                            self.warp = self.warp_range[self.warp_index]
                            self.set_warp_ui()
                    if e.key == self.keys["increase_time_warp"]:
                        if self.disable_warp_changing:
                            pass
                        elif self.warp_phys_active:
                            if self.warp_phys_index < len(self.warp_phys_range)-1:
                                self.warp_phys_index += 1
                                self.warp_phys = self.warp_phys_range[self.warp_phys_index]
                                self.set_warp_ui()
                        elif self.warp_index < len(self.warp_range)-1:
                            self.warp_index += 1
                            self.warp = self.warp_range[self.warp_index]
                            self.set_warp_ui()
                    if e.key == self.keys["stop_time_warp"]:
                        self.warp_phys_index = 0
                        self.warp_phys = self.warp_phys_range[self.warp_phys_index]
                        self.warp_index = 0
                        self.warp = self.warp_range[self.warp_index]
                        if self.warp_phys_active:
                            if self.warp_phys != 0:
                                self.set_warp_ui()
                        elif self.warp != 0:
                            self.set_warp_ui()

        elif e.type == pygame.KEYUP:
            self.hold_key = None

        # holding keys
        if self.hold_key:
            if self.hold_key == self.keys["rotate_cw"]:
                self.v_rot_dir = -1
            elif self.hold_key == self.keys["rotate_ccw"]:
                self.v_rot_dir = 1


    def input_mouse(self, e):
        """Input mouse for simulation"""
        self.mouse_raw = list(pygame.mouse.get_pos())
        self.mouse = list((self.mouse_raw[0]/self.zoom, -(self.mouse_raw[1] - self.screen_y)/self.zoom))   # mouse position on zoomed screen
        # y coordinate in self.mouse is negative for easier applying in formula to check if mouse is inside circle

        # disable input when mouse clicks on ui
        if not self.pause_menu and self.menu is None:
            if e.type == pygame.MOUSEBUTTONDOWN:
                if self.mouse_raw[0] <= self.btn_s or self.mouse_raw[1] <= 22:
                    if self.disable_ui is False:
                        self.disable_input = True
                        self.allow_keys = True
                else:
                    self.disable_input = False
                    self.allow_keys = False
                if self.right_menu is not None:
                    if self.disable_ui is False:
                        if self.mouse_raw[0] >= self.right_menu_x:
                            self.disable_input = True
                            self.allow_keys = True

        if not self.disable_input:
            # moving and selecting with lclick
            if e.type == pygame.MOUSEBUTTONDOWN:
                if e.button == 1:
                    self.move = True
                    self.mouse_old = self.mouse   # initial mouse position for movement
                    self.mouse_raw_old = self.mouse_raw

            if e.type == pygame.MOUSEBUTTONUP:
                if e.button == 1:
                    self.move = False
                    mouse_move = math.dist(self.mouse_raw, self.mouse_raw_old)
                    if e.button != 2:   # don't select body with middle click when in insert mode
                        if mouse_move < self.select_sensitivity:
                            # first check for vessels
                            for vessel, vessel_pos in enumerate(self.v_pos):
                                curve = self.screen_coords_array(self.v_curves[vessel])   # line coords on screen
                                diff = np.amax(curve, 0) - np.amin(curve, 0)
                                if diff[0]+diff[1] > 32:   # skip hidden vessels with too small orbits
                                    scr_radius = 11
                                    # if mouse is inside vessel radius on its location: (vessel_x - mouse_x)**2 + (vessel_y - mouse_y)**2 < radius**2
                                    if sum(np.square(self.screen_coords(vessel_pos) - self.mouse_raw)) < (scr_radius)**2:
                                        self.vessel_potential_target = vessel   # if clicked only once, timer must change target
                                        if self.first_click:
                                            prev_active_vessel = self.active_vessel
                                            self.active_vessel = vessel
                                            self.follow = 1
                                            self.vessel_potential_target = None
                                            self.target = self.v_ref[self.active_vessel]   # set new active vessel's parent to be target
                                            self.target_type = 0
                                            if self.ref[prev_active_vessel] == self.ref[vessel]:
                                                # calculate new follow offset so view does not move
                                                diff = self.v_pos[prev_active_vessel] - self.v_pos[self.active_vessel]
                                                self.follow_offset_x -= diff[0]
                                                self.follow_offset_y -= diff[1]
                                            else:
                                                # reset follow offset
                                                self.follow_offset_x = self.screen_x / 2
                                                self.follow_offset_y = self.screen_y / 2
                                        self.first_click = True
                            if not self.first_click:   # if vessel is selected: don't check for bodies
                                for body, body_pos in enumerate(self.pos):
                                    curve = self.screen_coords_array(self.curves[body])   # line coords on screen
                                    diff = np.amax(curve, 0) - np.amin(curve, 0)
                                    if body == 0 or diff[0]+diff[1] > 32:   # skip hidden bodies with too small orbits
                                        scr_radius = self.radius[body]*self.zoom
                                        if scr_radius < 5:   # if body is small on screen, there is marker
                                            scr_radius = 8
                                        # if mouse is inside body radius on its location: (body_x - mouse_x)**2 + (body_y - mouse_y)**2 < radius**2
                                        if sum(np.square(self.screen_coords(body_pos) - self.mouse_raw)) < (scr_radius)**2:
                                            self.target = body
                                            self.target_type = 0

            # mouse wheel: change zoom
            if not self.disable_input:
                if e.type == pygame.MOUSEWHEEL:   # change zoom
                    if self.zoom > self.zoom_step or e.y == 1:   # prevent zooming below zoom_step, zoom can't be 0, but allow zoom to increase
                        self.zoom_step = self.zoom / 10
                        self.zoom += e.y * self.zoom_step
                        # zoom translation to center
                        self.zoom_x += (self.screen_x / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_x / (self.zoom * 2))
                        self.zoom_y += (self.screen_y / 2 / (self.zoom - e.y * self.zoom_step)) - (self.screen_y / (self.zoom * 2))
                        # these values are added only to displayed objects, traces... But not to real position


    def ui_mouse(self, e):
        """Input mouse for menus"""
        btn_disable_input = False
        if self.disable_input and not self.allow_keys:
            btn_disable_input = True
        graphics.update_mouse(self.mouse_raw, self.click, btn_disable_input)
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            self.click = True

            # scroll bar
            if self.menu == 0 or self.menu == 1:
                scrollable_len = max(0, self.game_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                if scrollable_len != 0:
                    scrollbar_pos = self.scroll * scrollbar_limit / scrollable_len
                else:
                    scrollbar_pos = 0
                scrollbar_x = self.games_x + self.btn_w_l + self.space + 2
                scrollbar_y = self.games_y - self.space + 3 + scrollbar_pos
                if scrollbar_x <= self.mouse_raw[0]-1 <= scrollbar_x + 11 and scrollbar_y <= self.mouse_raw[1]-1 <= scrollbar_y + 40:
                    self.scrollbar_drag = True
                    self.scrollbar_drag_start = self.mouse[1]
                    self.ask = True   # dirty shortcut to disable safe buttons

        if e.type == pygame.MOUSEBUTTONUP and e.button == 1:
            if self.click:

                # pause menu
                if self.pause_menu:
                    y_pos = self.pause_y
                    for num, _ in enumerate(buttons_pause_menu):
                        if self.pause_x <= self.mouse_raw[0]-1 <= self.pause_x + self.btn_w and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                            if num == 0:   # resume
                                self.pause_menu = False
                                self.disable_input = False
                                self.set_pause(False)
                            elif num == 1:   # save
                                self.menu = 0
                                self.pause_menu = False
                                self.gen_game_list()
                            elif num == 2:   # load
                                self.menu = 1
                                self.pause_menu = False
                                self.gen_game_list()
                            elif num == 3:   # settings
                                self.state = 43   # go directly to main menu settings, but be able to return here
                            elif num == 4:   # quit
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.set_pause(False)
                            elif num == 5:   # save and quit
                                self.save(self.file_path, name=self.sim_name, silent=True)
                                self.state = 1
                                self.pause_menu = False
                                self.disable_input = False
                                self.set_pause(False)
                        y_pos += self.btn_h + self.space

                # disable scrollbar_drag when release click
                elif self.scrollbar_drag:
                    self.scrollbar_drag = False
                    self.ask = None

                # save
                elif self.menu == 0:
                    # new game
                    if self.new_game:
                        x_pos = self.ask_x
                        for num in [0, 1]:
                            if x_pos <= self.mouse_raw[0]-1 <= x_pos+self.btn_w_h and self.ask_y+self.space <= self.mouse_raw[1]-1 <= self.ask_y+self.space+self.btn_h:
                                if num == 0:   # cancel
                                    pass
                                elif num == 1:   # save
                                    path = peripherals.new_game(self.text, time.strftime("%d.%m.%Y %H:%M"))
                                    self.save(path, name=self.text)
                                    self.gen_game_list()
                                self.new_game = False
                                self.ask = None
                            x_pos += self.btn_w_h + self.space

                    else:   # disables underlaying menu
                        # games list
                        if self.games_y - self.space <= self.mouse_raw[1]-1 <= self.games_y + self.list_limit:
                            y_pos = self.games_y - self.scroll
                            for num, _ in enumerate(self.games[:, 1]):
                                if y_pos >= self.games_y - self.btn_h - self.space and y_pos <= self.games_y + self.list_limit:    # don't detect outside list area
                                    if self.games_x <= self.mouse_raw[0]-1 <= self.games_x + self.btn_w_l and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                                        self.selected_item = num
                                        self.selected_path = "Saves/" + self.games[self.selected_item, 0]
                                        if self.first_click == num:   # detect double click
                                            if self.file_path == self.selected_path:   # don't ask to save over current file
                                                self.save(self.file_path)
                                                self.menu = None
                                                self.pause_menu = False
                                                self.disable_input = False
                                            else:
                                                self.ask = "save"
                                            self.click = False   # dont carry click to ask window
                                        self.first_click = num
                                y_pos += self.btn_h + self.space

                        # ui
                        x_pos = self.games_x_ui
                        for num, text in enumerate(buttons_save):
                            if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h_3 and self.games_y_ui <= self.mouse_raw[1]-1 <= self.games_y_ui + self.btn_h:
                                if num == 0:   # cancel
                                    self.menu = None
                                    self.pause_menu = True
                                elif num == 1:   # save
                                    if self.file_path == self.selected_path:   # don't ask to save over current file
                                        self.save(self.file_path)
                                        self.menu = None
                                        self.pause_menu = False
                                        self.disable_input = False
                                    else:
                                        self.ask = "save"
                                elif num == 2:   # new save
                                    self.new_game = True
                                    self.ask = True   # dirty shortcut to disable safe buttons
                            x_pos += self.btn_w_h_3 + self.space

                # load
                elif self.menu == 1:
                    # games list
                    if self.games_y - self.space <= self.mouse_raw[1]-1 <= self.games_y + self.list_limit:
                        y_pos = self.games_y - self.scroll
                        for num, text in enumerate(self.games[:, 1]):
                            # don't detect outside list area
                            if y_pos >= self.games_y - self.btn_h - self.space and y_pos <= self.games_y + self.list_limit:
                                if self.games_x <= self.mouse_raw[0]-1 <= self.games_x + self.btn_w_l and y_pos <= self.mouse_raw[1]-1 <= y_pos + self.btn_h:
                                    self.selected_item = num
                                    self.selected_path = "Saves/" + self.games[self.selected_item, 0]
                                    if self.first_click == num:   # detect double click
                                        self.ask = "load"
                                        self.click = False   # dont carry click to ask window
                                    self.first_click = num
                            y_pos += self.btn_h + self.space

                    x_pos = self.games_x_ui
                    for num, text in enumerate(buttons_load):
                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h_2 and self.games_y_ui <= self.mouse_raw[1]-1 <= self.games_y_ui + self.btn_h:
                            if num == 0:   # cancel
                                self.menu = None
                                self.pause_menu = True
                            elif num == 1:   # save
                                self.ask = "load"
                        x_pos += self.btn_w_h_2 + self.space

                # settings
                elif self.menu == 2:
                    pass

            # ask
            if self.click:
                if self.ask is not None:
                    x_pos = self.ask_x
                    for num in [0, 1]:
                        if x_pos <= self.mouse_raw[0]-1 <= x_pos + self.btn_w_h and self.ask_y <= self.mouse_raw[1]-1 <= self.ask_y + self.btn_h:
                            if num == 0:   # cancel
                                pass
                            elif num == 1:   # yes
                                if self.ask == "load":
                                    self.load()
                                if self.ask == "save":
                                    self.save(self.selected_path)
                                    self.file_path = self.selected_path
                            self.menu = None
                            self.pause_menu = False
                            self.disable_input = False
                            self.ask = None
                        x_pos += self.btn_w_h + self.space

            if not self.disable_ui:
                # left ui
                y_pos = 23
                for num, _ in enumerate(self.ui_imgs):
                    if 0 <= self.mouse_raw[0] <= 0 + self.btn_s and y_pos <= self.mouse_raw[1] <= y_pos + self.btn_s:
                        if num == 0:   # menu
                            self.pause_menu = True
                            self.disable_input = True
                            self.set_pause(True)
                            self.right_menu = None
                        elif self.right_menu == num:
                            self.right_menu = None
                        elif num in [2, 3]:
                            if self.target is not None:
                                # don't display orbit data for root body
                                if num == 2 and self.target == self.ref[self.target] and self.target_type == 0:
                                    pass
                                # don't display body data for vessel
                                elif num == 3 and self.target_type == 1:
                                    pass
                                else:
                                    self.right_menu = num
                                    self.click = False

                        else:
                            self.right_menu = num
                    y_pos += self.btn_s + 1

                # top ui
                x_pos = 151
                for num, _ in enumerate(self.top_ui_imgs):
                    if x_pos <= self.mouse_raw[0] <= x_pos + self.btn_sm and 0 <= self.mouse_raw[1] <= self.btn_sm:
                        if num == 0:   # warp
                            if self.pause:
                                self.pause = not self.pause
                            elif self.disable_warp_changing:
                                self.warp_phys_index = 0
                                self.warp_phys = self.warp_phys_range[self.warp_phys_index]
                                self.warp_index = 0
                                self.warp = self.warp_range[self.warp_index]
                            elif self.warp_phys_active:
                                self.warp_phys_index += 1
                                if self.warp_phys_index >= len(self.warp_phys_range):
                                    self.warp_phys_index = 0
                                self.warp_phys = self.warp_phys_range[self.warp_phys_index]
                            else:
                                self.warp_index += 1
                                if self.warp_index >= len(self.warp_range):
                                    self.warp_index = 0
                                self.warp = self.warp_range[self.warp_index]
                            self.set_warp_ui()

                        if num == 1:
                            if self.active_vessel is not None:   # follow
                                self.follow += 1   # cycle follow modes (0-disabled, 1-active vessel, 2-orbited body)
                                if self.follow > 2:
                                    self.follow = 0
                                self.follow_offset_x = self.screen_x / 2
                                self.follow_offset_y = self.screen_y / 2
                                self.top_ui_imgs[1] = self.top_ui_img_follow[self.follow]
                                text = text_follow_mode[self.follow]
                                graphics.timed_text_init(
                                    rgb.gray0, self.fontmd,
                                    "Follow mode: " + text,
                                    (self.screen_x/2, self.screen_y-70), 1.5, True,
                                )
                        if num == 2:
                            self.grid_mode += 1   # grid
                            if self.grid_mode > 3:
                                self.grid_mode = 0
                            self.top_ui_imgs[2] = self.top_ui_img_grid[self.grid_mode]
                            text = text_grid_mode[self.grid_mode]
                            graphics.timed_text_init(
                                rgb.gray0, self.fontmd,
                                "Grid mode: " + text,
                                (self.screen_x/2, self.screen_y-70), 1.5, True,
                            )
                    x_pos += self.btn_sm + 1

            # right ui
                if not self.click_timer:
                    if self.right_menu == 1:   # body list
                        y_pos = 38
                        for num, _ in enumerate(self.names):
                            if self.r_menu_x_btn <= self.mouse_raw[0]-1 <= self.r_menu_x_btn + 280 and y_pos <= self.mouse_raw[1]-1 <= y_pos + 21:
                                self.target = num
                                self.target_type = 0
                            y_pos += 26

            # scrollbar
            if e.type == pygame.MOUSEWHEEL and (self.menu == 0 or self.menu == 1):
                if self.scrollbar_drag is False:
                    # scrolling inside list area
                    if self.games_x-self.space <= self.mouse_raw[0]-1 <= self.games_x+self.btn_w_l+self.space+16 and self.games_y-self.space <= self.mouse_raw[1]-1 <= self.games_y+self.list_limit:
                        self.scroll -= e.y * self.scroll_sensitivity
                        if self.scroll < 0:
                            self.scroll = 0
                        elif self.scroll > max(0, self.game_list_size - self.list_limit):
                            self.scroll = max(0, self.game_list_size - self.list_limit)

            self.click = False

        # moving scrollbar with cursor
        if self.scrollbar_drag:
            if self.menu == 0 or self.menu == 1:
                scrollbar_pos = self.mouse_raw[1] - self.games_y
                scrollable_len = max(0, self.game_list_size - self.list_limit)
                scrollbar_limit = self.list_limit - 40 + 4
                self.scroll = scrollable_len * scrollbar_pos / scrollbar_limit
                if self.scroll < 0:
                    self.scroll = 0
                elif self.scroll > max(0, self.game_list_size - self.list_limit):
                    self.scroll = max(0, self.game_list_size - self.list_limit)

        return self.state


    def physics(self, e):
        """Do simulation physics with warp and pause"""
        if e.type == pygame.USEREVENT:
            debug_time = time.time()   # DEBUG
            if self.pause is False:
                # regular/physical warp toggle
                situation, alarm_vessel, physical_hold = physics_vessel.check_warp(self.warp)
                if situation == 0:   # space -> impact
                    if not self.warp_phys_active:
                        self.warp_phys_active = True
                        self.warp_phys = 1
                        self.warp_phys_index = 0
                        graphics.timed_text_init(
                            rgb.orange, self.fontmd,
                            f"Vessel {self.v_names[alarm_vessel]} is about to impact, switching to physical warp.",
                            (self.screen_x/2, self.screen_y-70), 1.5, True,
                        )
                    self.set_warp_ui(silent=True)
                elif situation == 1:   # space -> atmosphere
                    if not self.warp_phys_active:
                        self.warp_phys_active = True
                        self.warp_phys = 1
                        self.warp_phys_index = 0
                        graphics.timed_text_init(
                            rgb.orange, self.fontmd,
                            f"Vessel {self.v_names[alarm_vessel]} is entering atmosphere, switching to physical warp.",
                            (self.screen_x/2, self.screen_y-70), 1.5, True,
                        )
                    self.set_warp_ui(silent=True)
                elif situation == 2:   # atmosphere -> space
                    if self.warp_phys_active:
                        if physical_hold <= 0:
                            self.warp_phys_active = False
                            self.warp_phys = 1
                            self.warp_phys_index = 0
                            self.warp = 1
                            self.warp_index = 0
                            graphics.timed_text_init(
                                rgb.gray0, self.fontmd,
                                f"Vessel {self.v_names[alarm_vessel]} left atmosphere, switching to regular warp.",
                                (self.screen_x/2, self.screen_y-70), 1.5, True,
                            )
                        else:
                            graphics.timed_text_init(
                                rgb.gray0, self.fontmd,
                                f"Vessel {self.v_names[alarm_vessel]} left atmosphere, NOT switching to regular warp ({physical_hold} vessel/s are still in physical).",
                                (self.screen_x/2, self.screen_y-70), 1.5, True,
                            )
                    self.set_warp_ui(silent=True)
                elif situation == 3:   # crossing coi
                    self.vessel_crossing = alarm_vessel
                    self.disable_warp_changing = True
                    if self.warp_phys_active:
                        if self.warp_phys_mem is None:
                            self.warp_phys_mem = self.warp_phys_index
                        self.warp_phys = 1
                        self.warp_phys_index = 0
                    else:
                        if self.warp_mem is None:
                            self.warp_mem = self.warp_index
                        self.warp = 1
                        self.warp_index = 0
                        if self.warp_index > 5:
                            graphics.timed_text_init(
                                rgb.gray0, self.fontmd,
                                f"Vessel {self.v_names[self.vessel_crossing]} is about to pass COI, warp will be held for that period",
                                (self.screen_x/2, self.screen_y-70), 1.5, True,
                            )

                # for each vessel run prediction at Pe and Ap, it is warp independant
                physics_vessel.predict_enter_coi_service()
                # physical warp
                if self.warp_phys_active:
                    for _ in range(self.warp_phys):
                        self.pos, self.ma, ea = physics_body.move(self.warp_phys)
                        self.v_pos, self.v_ma = physics_vessel.move(self.warp_phys, self.pos, self.ma, ea)
                        self.v_rot_angle = physics_vessel.rotate(self.warp, self.active_vessel, self.v_rot_dir)
                        self.change_vessel = physics_vessel.cross_coi()
                    self.sim_time += 1 * self.warp_phys   # iterate sim_time
                # regular warp
                else:
                    self.pos, self.ma, ea = physics_body.move(self.warp)
                    self.v_pos, self.v_ma = physics_vessel.move(self.warp, self.pos, self.ma, ea)
                    self.v_rot_angle = physics_vessel.rotate(self.warp, self.active_vessel, self.v_rot_dir)
                    self.change_vessel = physics_vessel.cross_coi()
                    self.sim_time += 1 * self.warp   # iterate sim_time

                self.v_rot_dir = 0
                self.curves = physics_body.curve_move()

                # handling changes on vessel orbit
                if self.change_vessel is not None:
                    vessel_data, vessel_orb_data = physics_vessel.change_vessel(self.change_vessel)
                    self.update_vessel(self.change_vessel, vessel_data, vessel_orb_data)

                    # resuming warp after orbit changes
                    if self.vessel_crossing is not None and self.change_vessel == self.vessel_crossing:
                        self.disable_warp_changing = False
                        if self.warp_phys_active:
                            if self.warp_phys_mem is None:
                                self.warp_phys_mem = 0
                            self.warp_phys_index = self.warp_phys_mem
                            self.warp_phys = self.warp_phys_range[self.warp_phys_index]
                            self.warp_phys_mem = None
                        else:
                            if self.warp_mem is None:
                                self.warp_mem = 0
                            self.warp_index = self.warp_mem
                            self.warp = self.warp_range[self.warp_index]
                            self.warp_mem = None
                        if self.warp or self.warp_phys:
                            graphics.timed_text_init(
                                rgb.gray0, self.fontmd,
                                f"Vessel {self.v_names[self.vessel_crossing]} passed COI, warp was held for that period",
                                (self.screen_x/2, self.screen_y-70), 1.5, True,
                            )
                        self.vessel_crossing = None
                    self.change_vessel = None

                self.v_curves = physics_vessel.curve_move()

            # culing
            sim_screen = np.array((self.sim_coords((0, 0)), self.sim_coords(self.screen_dim)))
            self.visible_bodies, self.visible_coi, self.visible_body_orbits = physics_body.culling(sim_screen, self.zoom)
            self.visible_vessels, self.visible_vessel_orbits = physics_vessel.culling(sim_screen, self.zoom, self.visible_coi)
            self.curve_light, self.curve_dark, self.intersect, self.intersect_type, self.intersect_time, self.select_range = physics_vessel.curve_segments()

            self.physics_debug_time = time.time() - debug_time   # DEBUG


    def graphics(self, screen):
        """Draw simulation stuff on screen"""
        screen.fill((0, 0, 0))

        # follow vessel (this must be before drawing objects to prevent them from vibrating when moving)
        if self.follow:
            if self.active_vessel is not None:
                if self.follow == 1:
                    self.offset_x = - self.v_pos[self.active_vessel, 0] + self.follow_offset_x
                    self.offset_y = - self.v_pos[self.active_vessel, 1] + self.follow_offset_y
                else:
                    ref = self.v_ref[self.active_vessel]
                    self.offset_x = - self.pos[ref, 0] + self.follow_offset_x
                    self.offset_y = - self.pos[ref, 1] + self.follow_offset_y
            else:
                self.follow = 0


        # screen movement
        if self.move:   # this is not in userevent to allow moving while paused
            if self.mouse_fix_x:   # when mouse jumps from one edge to other:
                self.mouse_old[0] = self.mouse[0]   # don't calculate that as mouse movement
                self.mouse_fix_x = False
            if self.mouse_fix_y:
                self.mouse_old[1] = self.mouse[1]
                self.mouse_fix_y = False

            if self.follow:
                self.follow_offset_x += self.mouse[0] - self.mouse_old[0]
                self.follow_offset_y += self.mouse[1] - self.mouse_old[1]
            else:
                self.offset_x += self.mouse[0] - self.mouse_old[0]   # add mouse movement to offset
                self.offset_y += self.mouse[1] - self.mouse_old[1]

            if self.mouse_warp:
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

        # DRAWING ORDER: body stuff, vessel orbit, body, vessel, vessel stuff

        # draw body atmosphere (before everything else because it is fake transparent)
        for body in self.visible_bodies:
            scr_body_radius = self.radius[body] * self.zoom
            if scr_body_radius >= 5:
                if self.atm_h[body]:
                    atm_color = np.array(self.color[body]) * 30 / 255   # fake transparency
                    # atm_color = tuple(np.append(self.color[body], 30))   # real transparency - slow
                    scr_atm_radius = (self.radius[body] + self.atm_h[body]) * self.zoom
                    if scr_atm_radius > scr_body_radius + 2:
                        screen_coords = self.screen_coords(self.pos[body])
                        graphics.draw_circle_fill(screen, atm_color, screen_coords, scr_atm_radius)

        # background stars
        if self.bg_stars_enable:
            if self.follow and self.active_vessel is not None:
                parent_pos = self.pos[self.v_ref[self.active_vessel]]
            else:
                parent_pos = np.zeros(2)
                self.offset_old = np.array([self.offset_x, self.offset_y])
            # movement vector in one iterration relative to vessel parent
            offset_diff = self.offset_old - (np.array([self.offset_x, self.offset_y]) + parent_pos)
            offset_diff = offset_diff * min(self.zoom, 3)   # add zoom to speed calculation and limit zoom
            self.offset_old = np.array([self.offset_x, self.offset_y]) + parent_pos
            speed = math.sqrt(offset_diff.dot(offset_diff))/3   # speed as movement vector magnitude
            while speed > 300:   # limits speed when view is jumping (focus home, distant body...)
                speed = math.sqrt(speed)
            direction = math.atan2(offset_diff[1], offset_diff[0])   # movement vector angle from atan2
            bg_stars.draw_bg(screen, speed, direction, self.zoom)


        # background lines grid
        if self.grid_mode:
            if self.grid_mode == 1:   # grid mode: home
                origin = self.screen_coords([0, 0])
            if self.target is not None:
                if self.grid_mode == 2:      # grid mode: selected body
                    origin = self.screen_coords(self.v_pos[self.active_vessel])
                elif self.grid_mode == 3:   # grid mode: orbited body
                    origin = self.screen_coords(self.pos[self.v_ref[self.active_vessel]])
            else:
                origin = self.screen_coords([0, 0])
            graphics.draw_grid(screen, origin, self.zoom)


        # bodies stuff drawing, WITHOUT bodies - bodies are drawn aftter vessel orbit lines
        # draw body orbit curve lines
        for body in self.visible_body_orbits:
            curve = self.screen_coords_array(self.curves[body])
            if body != 0:
                line_color = np.where(self.color[body] > 255, 255, self.color[body])
                graphics.draw_lines(screen, tuple(line_color), curve, 2)

        for body in self.visible_bodies:
            scr_body_radius = self.radius[body] * self.zoom

            # target body
            if self.target is not None and self.target_type == 0 and self.target == body:
                body_pos = self.pos[body, :]
                ta, pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert = physics_body.selected(body)
                if self.right_menu == 2:
                    self.orbit_data_menu = [
                        self.pe_d[body],
                        self.ap_d[body],
                        self.ecc[body],
                        self.pea[body] * 180 / np.pi,
                        self.ma[body] * 180 / np.pi,
                        ta * 180 / np.pi,
                        self.dr[body],
                        distance,
                        self.period[body],
                        speed_orb,
                        speed_hor,
                        speed_vert,
                    ]

                # circles
                if not self.disable_labels:
                    # target selection
                    if body in self.visible_bodies:
                        if scr_body_radius >= 5:
                            # selection circle
                            scr_atm_radius = (self.radius[body] + self.atm_h[body]) * self.zoom
                            graphics.draw_circle(screen, rgb.cyan, self.screen_coords(body_pos), scr_atm_radius + 4, 1)
                        else:
                            # marker img
                            graphics.draw_img(screen, self.target_img, self.screen_coords(body_pos), center=True)

                    # circle of influence
                    if body in self.visible_coi and self.radius[body] < self.coi[body]:
                        graphics.draw_circle(screen, rgb.gray2, self.screen_coords(body_pos), self.coi[body] * self.zoom, 1)

        for body in self.visible_body_orbits:
            if self.target is not None and self.target_type == 0 and self.target == body:
                if not self.disable_labels:
                    if body != 0:
                        parent = self.ref[body]
                        parent_scr = self.screen_coords(self.pos[parent])
                        ta, pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert = physics_body.selected(body)
                        # ap and pe
                        if self.ap_d[body] > 0:
                            ap_scr = self.screen_coords(ap)
                        else:   # in case of hyperbola/parabola (ap_d is negative)
                            ap_scr = self.screen_coords(pe)
                        scr_dist = abs(parent_scr - ap_scr)
                        if scr_dist[0] > 18 or scr_dist[1] > 15:   # don't draw Ap and Pe if Ap is too close to parent

                            pe_scr = self.screen_coords(pe)
                            pe_scr_dist = abs(parent_scr - pe_scr)
                            if pe_scr_dist[0] > 18 or pe_scr_dist[1] > 18:   # don't draw Pe if it is too close to parent
                                # periapsis location marker, text: distance and time to it
                                pe_scr = self.screen_coords(pe)
                                graphics.draw_circle_fill(screen, rgb.lime1, pe_scr, 3)   # periapsis marker
                                graphics.text(
                                    screen, rgb.lime1, self.fontsm,
                                    "Periapsis: " + metric.format_si(self.pe_d[body], 2),
                                    (pe_scr[0], pe_scr[1] + 7), True,
                                )
                                graphics.text(
                                    screen, rgb.lime1, self.fontsm,
                                    "T - " + format_time.to_date(int(pe_t/self.ptps)),
                                    (pe_scr[0], pe_scr[1] + 17), True,
                                )

                            if self.ecc[body] < 1:   # if orbit is ellipse
                                # apoapsis location marker, text: distance and time to it
                                graphics.draw_circle_fill(screen, rgb.lime1, ap_scr, 3)   # apoapsis marker
                                graphics.text(
                                    screen, rgb.lime1, self.fontsm,
                                    "Apoapsis: " + metric.format_si(self.ap_d[body], 2),
                                    (ap_scr[0], ap_scr[1] + 7), True,
                                )
                                graphics.text(
                                    screen, rgb.lime1, self.fontsm,
                                    "T - " + format_time.to_date(int(ap_t/self.ptps)),
                                    (ap_scr[0], ap_scr[1] + 17), True,
                                )

        # draw vessel orbit curve lines
        for vessel in self.visible_vessel_orbits:
            # get curve intersections and ranges
            curve_light = self.screen_coords_array(self.curve_light[vessel])
            curve_dark = self.screen_coords_array(self.curve_dark[vessel])
            intersect_type = self.intersect_type[vessel]
            vessel_pos = self.screen_coords(self.v_pos[vessel])
            # active vessel
            if self.active_vessel is not None and self.active_vessel == vessel:
                if intersect_type in [1, 3]:
                    graphics.draw_lines(screen, rgb.cyan_1, curve_dark, 2)
                graphics.draw_lines(screen, rgb.cyan, curve_light, 2)
            # target vessel
            elif self.target is not None and self.target_type == 1 and self.target == vessel:
                if intersect_type in [1, 3]:
                    graphics.draw_lines(screen, rgb.gray1, curve_dark, 2)
                graphics.draw_lines(screen, rgb.gray, curve_light, 2)
            else:
                if intersect_type in [1, 3]:
                    graphics.draw_lines(screen, rgb.gray2, curve_dark, 2)
                graphics.draw_lines(screen, rgb.gray1, curve_light, 2)

        # bodies drawing
        for body in self.visible_bodies:
            scr_body_radius = self.radius[body] * self.zoom
            body_color = tuple(self.color[body])
            if scr_body_radius >= 5:
                if self.types[body] != 4:
                    graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.pos[body]), scr_body_radius)
                else:   # black hole
                    graphics.draw_circle_fill(screen, rgb.black, self.screen_coords(self.pos[body]), scr_body_radius)
                    graphics.draw_circle(screen, rgb.white, self.screen_coords(self.pos[body]), scr_body_radius, 2)
            else:   # if body is too small, draw marker with fixed size
                graphics.draw_circle_fill(screen, rgb.gray1, self.screen_coords(self.pos[body]), 6)
                graphics.draw_circle_fill(screen, rgb.gray2, self.screen_coords(self.pos[body]), 5)
                graphics.draw_circle_fill(screen, body_color, self.screen_coords(self.pos[body]), 4)


        # vessel stuff drawing WITH vessels
        for vessel in self.visible_vessel_orbits:
            # get curve intersections and ranges
            curve_light = self.screen_coords_array(self.curve_light[vessel])
            curve_dark = self.screen_coords_array(self.curve_dark[vessel])
            intersect = self.screen_coords(self.intersect[vessel])
            time_to_intersect = self.intersect_time[vessel]
            intersect_type = self.intersect_type[vessel]
            vessel_pos = self.screen_coords(self.v_pos[vessel])
            vessel_rot = self.v_rot_angle[vessel]
            target = self.target_type == 1 and self.target == vessel
            active = self.active_vessel is not None and self.active_vessel == vessel

            if active:
                graphics.draw_img(screen, self.vessel_img, vessel_pos, angle=vessel_rot-np.pi/2, scale=0.75, center=True)

            # active vessel and target vessel
            if active or target:

                # parent circle of influence
                if not self.disable_labels:
                    ta, pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert = physics_vessel.selected(vessel)
                    ref = self.v_ref[vessel]
                    parent_scr = self.screen_coords(self.pos[ref])
                    if ref != 0 and ref in self.visible_coi:
                        graphics.draw_circle(screen, rgb.gray2, parent_scr, self.coi[ref] * self.zoom, 1)

                    # ap and pe
                    if self.v_ap_d[vessel] > 0:
                        ap_scr = self.screen_coords(ap)
                    else:   # in case of hyperbola/parabola (ap_d is negative)
                        ap_scr = self.screen_coords(pe)
                    scr_dist = abs(parent_scr - ap_scr)
                    if scr_dist[0] > 8 or scr_dist[1] > 8:   # don't draw Ap and Pe if Ap is too close to parent

                        pe_scr = self.screen_coords(pe)
                        parent_rad = [self.radius[ref] * self.zoom] * 2
                        pe_scr_dist = abs(parent_scr - pe_scr) - parent_rad
                        if pe_scr_dist[0] > 2 or pe_scr_dist[1] > 2:   # don't draw Pe if it is too close to parent
                            # periapsis location marker, text: distance and time to it
                            in_range = point_between(
                                0,
                                self.select_range[vessel, 0],
                                self.select_range[vessel, 1],
                                self.v_dr[vessel],
                            )
                            if intersect_type != 2 or (intersect_type == 2 and in_range):
                                pe_scr = self.screen_coords(pe)
                                graphics.draw_circle_fill(screen, rgb.lime1, pe_scr, 3)   # periapsis marker
                                graphics.text(
                                    screen, rgb.lime1, self.fontsm,
                                    "Periapsis: " + str(round(self.v_pe_d[vessel], 1)),
                                    (pe_scr[0], pe_scr[1] + 7), True,
                                )
                                graphics.text(
                                    screen, rgb.lime1, self.fontsm,
                                    "T - " + format_time.to_date(int(pe_t/self.ptps)),
                                    (pe_scr[0], pe_scr[1] + 17), True,
                                )

                        if self.v_ecc[vessel] < 1:   # if orbit is ellipse
                            if self.v_ap_d[vessel] <= self.coi[ref]:
                                # apoapsis location marker, text: distance and time to it
                                in_range = point_between(
                                    np.pi,
                                    self.select_range[vessel, 0],
                                    self.select_range[vessel, 1],
                                    self.v_dr[vessel],
                                )
                                if intersect_type != 2 or (intersect_type == 2 and in_range):
                                    graphics.draw_circle_fill(screen, rgb.lime1, ap_scr, 3)   # apoapsis marker
                                    graphics.text(
                                        screen, rgb.lime1, self.fontsm,
                                        "Apoapsis: " + str(round(self.v_ap_d[vessel], 1)),
                                        (ap_scr[0], ap_scr[1] + 7), True,
                                    )
                                    graphics.text(
                                        screen, rgb.lime1, self.fontsm,
                                        "T - " + format_time.to_date(int(ap_t/self.ptps)),
                                        (ap_scr[0], ap_scr[1] + 17), True,
                                    )

                        # characteristic points
                        if intersect_type == 1:   # impact
                            if self.radius[ref] * self.zoom >= 5:
                                graphics.draw_img(screen, self.impact_img, intersect, center=True)
                                graphics.text(
                                    screen, rgb.lime1, self.fontsm,
                                    "T - " + format_time.to_date(int(time_to_intersect/self.ptps)),
                                    (intersect[0], intersect[1] + 10), True,
                                )
                        elif intersect_type == 2:   # enter COI
                            if self.coi[ref] * self.zoom >= 10:
                                if active:
                                    graphics.draw_img(screen, self.orb_enter_img_cyan, intersect, center=True)
                                    graphics.text(
                                        screen, rgb.lime1, self.fontsm,
                                        "T - " + format_time.to_date(int(time_to_intersect/self.ptps)),
                                        (intersect[0], intersect[1] + 10), True,
                                    )
                                else:
                                    graphics.draw_img(screen, self.orb_enter_img_gray, intersect, center=True)
                        elif intersect_type == 3:   # leave COI
                            if self.coi[ref] * self.zoom >= 10:
                                if active:
                                    graphics.draw_img(screen, self.orb_leave_img_cyan, intersect, center=True)
                                    graphics.text(
                                        screen, rgb.lime1, self.fontsm,
                                        "T - " + format_time.to_date(int(time_to_intersect/self.ptps)),
                                        (intersect[0], intersect[1] + 10), True,
                                    )
                                else:
                                    graphics.draw_img(screen, self.orb_leave_img_gray, intersect, center=True)

            # target vessel
            if self.target is not None and self.target_type == 1 and self.target == vessel:
                graphics.draw_img(screen, self.vessel_img, vessel_pos, angle=vessel_rot-np.pi/2, scale=0.75, center=True)
                graphics.draw_img(screen, self.target_img, vessel_pos, center=True)
                ta, pe, pe_t, ap, ap_t, distance, speed_orb, speed_hor, speed_vert = physics_vessel.selected(vessel)
                if self.right_menu == 2:
                    self.orbit_data_menu = [
                        self.v_pe_d[vessel],
                        self.v_ap_d[vessel],
                        self.v_ecc[vessel],
                        self.v_pea[vessel] * 180 / np.pi,
                        self.v_ma[vessel] * 180 / np.pi,
                        ta * 180 / np.pi,
                        self.v_dr[vessel],
                        distance,
                        self.v_period[vessel],
                        speed_orb,
                        speed_hor,
                        speed_vert,
                    ]

            # all other vessels
            elif vessel in self.visible_vessels:
                graphics.draw_img(screen, self.vessel_img, vessel_pos, angle=vessel_rot-np.pi/2, scale=0.75, center=True)


    def graphics_ui(self, screen, clock):
        """Draw GUI menus"""

        # pause menu
        if self.pause_menu:
            border_rect = [self.pause_x-self.space, self.pause_y-self.space, self.btn_w+2*self.space, self.pause_max_y]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
            graphics.buttons_vertical(screen, buttons_pause_menu, (self.pause_x, self.pause_y), safe=True)

        # save menu
        if self.menu == 0:
            border_rect = [self.games_x-2*self.space, self.games_y-2*self.space, self.btn_w_l+4*self.space + 16, self.games_max_y+3*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            graphics.buttons_list(screen, self.games[:, 1], (self.games_x, self.games_y), self.list_limit, self.scroll, self.selected_item, safe=not bool(self.ask))
            graphics.buttons_horizontal(screen, buttons_save, (self.games_x_ui, self.games_y_ui), alt_width=self.btn_w_h_3, safe=not bool(self.ask))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)

        # load menu
        elif self.menu == 1:
            border_rect = [self.games_x-2*self.space, self.games_y-2*self.space, self.btn_w_l+4*self.space + 16, self.games_max_y+3*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            graphics.buttons_list(screen, self.games[:, 1], (self.games_x, self.games_y), self.list_limit, self.scroll, self.selected_item, safe=not bool(self.ask))
            graphics.buttons_horizontal(screen, buttons_load, (self.games_x - self.space, self.games_y_ui), alt_width=self.btn_w_h_2, safe=not bool(self.ask))
            pygame.draw.rect(screen, rgb.white, border_rect, 1)

        # asking to load/save
        if self.ask == "load":
            ask_txt = "Loading will overwrite unsaved changes."
            graphics.ask(screen, ask_txt, self.games[self.selected_item, 1], "Load", (self.ask_x, self.ask_y))
        elif self.ask == "save":
            ask_txt = "Are you sure you want to overwrite this save:"
            graphics.ask(screen, ask_txt, self.games[self.selected_item, 1], "Save", (self.ask_x, self.ask_y))

        # screenshot
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

        # new game
        if self.new_game:
            border_rect = [self.ask_x-self.space, self.ask_y-40-self.btn_h, self.btn_w_h*2+3*self.space, self.btn_h+40+self.btn_h+2*self.space]
            bg_rect = [sum(i) for i in zip(border_rect, [-10, -10, 20, 20])]
            pygame.draw.rect(screen, rgb.black, bg_rect)
            pygame.draw.rect(screen, rgb.white, border_rect, 1)
            graphics.text(
                screen, rgb.white, self.fontbt,
                "New Save",
                (self.screen_x/2, self.ask_y-20-self.btn_h), True,
            )
            textinput.graphics(screen, clock, self.fontbt, (self.ask_x, self.ask_y-self.btn_h), (self.btn_w_h*2+self.space, self.btn_h))
            graphics.buttons_horizontal(screen, buttons_new_game, (self.ask_x, self.ask_y+self.space), safe=True)

        # double click counter (not graphics related, but must be outside of input functions)
        if self.first_click is not None:
            self.click_timer += clock.get_fps() / 60
            if self.click_timer >= 0.4 * 60:
                self.first_click = None
                self.click_timer = 0
                # if only once is clicked on vessel, timer has to change target to it
                if self.vessel_potential_target is not None:
                    if self.vessel_potential_target != self.active_vessel:
                        self.target = self.vessel_potential_target
                        self.target_type = 1
                        self.vessel_potential_target = None

        if not self.disable_ui:
            graphics.timed_text(screen)

            # left ui
            pygame.draw.rect(screen, rgb.black, (0, 0, self.btn_s, self.screen_y))
            if self.target is not None:
                prop_l = None
                if self.target_type == 0:
                    if self.target == self.ref[self.target]:
                        prop_l = [None, None, 0, None]
                else:
                    prop_l = [None, None, None, 0]   # don't display body data for vessel
            else:
                prop_l = [None, None, 0, 0]
            graphics.buttons_small_v(screen, self.ui_imgs, (0, 23), prop=prop_l, selected=self.right_menu)
            pygame.draw.line(screen, rgb.white, (self.btn_s, 0), (self.btn_s, self.screen_y), 1)

            # right ui
            if self.right_menu is not None:
                pygame.draw.rect(screen, rgb.black, (self.right_menu_x, 0, 300, self.screen_y))
                pygame.draw.line(screen, rgb.white, (self.right_menu_x, 0), (self.right_menu_x, self.screen_y))

            if self.right_menu == 1:   # body list
                imgs = []
                names_screen = []
                for num, name in enumerate(self.names):
                    if num == 0:
                        names_screen.append("Root: " + graphics.limit_text(name, self.fontbt, 280))
                    else:
                        parent = self.names[self.ref[num]]
                        names_screen.append(graphics.limit_text(name, self.fontbt, 280) + "    @ " + parent)
                    imgs.append(self.body_imgs[int(self.types[num])])
                graphics.text_list_select(screen, names_screen, (self.r_menu_x_btn, 38), (280, 21), 26, self.target, imgs)

            elif self.right_menu == 2 and self.target is not None:   # data orbit
                texts = text_data_orb[:]
                for num, _ in enumerate(text_data_orb):
                    if num == 0:
                        if self.target_type == 0:
                            texts[0] = texts[0] + self.names[self.target]
                        else:
                            texts[0] = texts[0] + self.v_names[self.target]
                    elif num == 1:
                        if self.target_type == 0:
                            texts[1] = texts[1] + self.names[self.ref[self.target]]
                        else:
                            texts[1] = texts[1] + self.names[self.v_ref[self.target]]
                    elif num == 8:
                        if self.orbit_data_menu[6] == -1:
                            texts[8] = texts[8] + "Clockwise"
                        else:
                            texts[8] = texts[8] + "Counter-clockwise"
                    elif num == 10:
                        texts[10] = texts[10] + format_time.to_date(int(self.orbit_data_menu[8]/self.ptps))
                    else:
                        texts[num] = texts[num] + metric.format_si(self.orbit_data_menu[num-2], 3)
                graphics.text_list(screen, texts, (self.r_menu_x_btn, 38), (280, 21), 26)

            elif self.right_menu == 3 and self.target is not None and self.target_type == 0:   # data body
                values_body = [self.names[self.target],
                               body_types[int(self.types[self.target])],
                               metric.format_si(self.mass[self.target], 3),
                               metric.format_si(self.density[self.target], 3),
                               metric.format_si(self.radius[self.target], 3),
                               metric.format_si(self.coi[self.target], 3)]
                texts_body = []
                for i, _ in enumerate(text_data_body):
                    texts_body.append(text_data_body[i] + values_body[i])
                texts_merged = texts_body[:]
                if int(self.types[self.target]) in [0, 1, 2]:   # dwarf, planet, gas
                    color = self.color[self.target]
                    values_planet = [
                        "WIP",
                        " R: " + str(color[0]) + "   G: " + str(color[1]) + "   B: " + str(color[2]),
                        metric.format_si(self.atm_h[self.target], 3),
                        metric.format_si(self.surf_grav[self.target], 3),
                    ]
                    texts_planet = []
                    for i, _ in enumerate(text_data_planet):
                        if isinstance(values_planet[i], str):
                            texts_planet.append(text_data_planet[i] + values_planet[i])
                        else:
                            texts_planet.append(values_planet[i])
                    texts_merged += texts_planet
                elif int(self.types[self.target]) == 3:   # star
                    values_star = [
                        metric.format_si(self.temp[self.target], 3) + "°K",
                        metric.format_si(self.luminosity[self.target], 3) + "W",
                        self.stellar_class[self.target],
                    ]
                    texts_star = []
                    for i, _ in enumerate(text_data_star):
                        texts_star.append(text_data_star[i] + values_star[i])
                    texts_merged += texts_star
                elif int(self.types[self.target]) == 4:   # for bh
                    values_bh = [metric.format_si(self.rad_sc[self.target], 3)]
                    texts_bh = []
                    for i, _ in enumerate(text_data_bh):
                        texts_bh.append(text_data_bh[i] + values_bh[i])
                    texts_merged += texts_bh
                graphics.text_list(screen, texts_merged, (self.r_menu_x_btn, 38), (280, 21), 26)

            # top ui
            pygame.draw.rect(screen, rgb.black, (0, 0, self.screen_x, 22))
            pygame.draw.line(screen, rgb.white, (0, 22), (self.screen_x, 22), 1)
            graphics.text(
                screen, rgb.white, self.fontmd,
                format_time.to_date(int(self.sim_time/self.ptps), False),
                (74, 11), center=True,
            )
            pygame.draw.line(screen, rgb.white, (150, 0), (150, 22), 1)
            graphics.buttons_small_h(screen, self.top_ui_imgs, (151, 0))

            # DEBUG
            graphics.text(screen, rgb.gray1, self.fontmd, str(self.mouse_raw), (self.screen_x - 240, 2))
            if self.debug_timer < 10:
                self.debug_timer += 1
                self.physics_debug_time_sum += self.physics_debug_time
            else:
                self.debug_timer = 0
                self.physics_debug_percent = round((self.physics_debug_time_sum/10 * 100) / (1 / max(clock.get_fps(), 1)), 1)
                self.physics_debug_time_sum = 0
            graphics.text(
                screen, rgb.gray1, self.fontmd,
                "phys: " + str(self.physics_debug_percent) + "%",
                (self.screen_x - 150, 2),
            )
            graphics.text(
                screen, rgb.gray1, self.fontmd,
                "fps: " + str(int(clock.get_fps())),
                (self.screen_x - 50, 2),
            )


    def main(self, screen, clock):
        """Main game loop"""
        run = True
        while run:
            for event in pygame.event.get():
                self.input_keys(event)
                self.input_mouse(event)
                self.ui_mouse(event)
                if self.state != 2:
                    state = self.state
                    self.state = 2
                    return state
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                self.physics(event)
                self.autosave(event)
            self.graphics(screen)
            self.graphics_ui(screen, clock)
            pygame.display.flip()
            clock.tick()
        return self.state
