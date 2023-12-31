import pygame as pg


settings = {"first_run": "True",
            "resolution": [1366, 768],
            "fullscreen": "True",
            "vsync": "True",
            "curve_points": 100,
            "culling": "False",
            "grid_spacing_min": 100,
            "grid_spacing_max": 200,
            "mouse_wrap": "True",
            "antialiasing": "True",
            "stars_antialiasing": "False",
            "stars_num": 400,
            "stars_new_color": "False",
            "extra_frame": 1000,
            "stars_speed_mult": 1,
            "stars_opacity": 0.7,
            "cluster_enable": "True",
            "cluster_new": "False",
            "cluster_num": 6,
            "cluster_star": [10, 30],
            "cluster_size_mult": [2, 4],
            "stars_radius": [0.6, 0.3, 0.1],
            "stars_speed": [0.5, 0.3, 0.2],
            "stars_zoom_min": 0.5,
            "stars_zoom_max": 2,
            "zoom_mult": 5,
            "stars": "True",
            "autosave_time": 5,
            "numba": "True",
            "fastmath": "False"
            }


keybindings = {"forward": pg.K_w,
               "backward": pg.K_s,
               "left": pg.K_a,
               "right": pg.K_d,
               "interactive_pause": pg.K_SPACE,
               "increase_time_warp": pg.K_PERIOD,
               "decrease_time_warp": pg.K_COMMA,
               "stop_time_warp": pg.K_SLASH,
               "focus_home": pg.K_h,
               "cycle_follow_modes": pg.K_f,
               "cycle_grid_modes": pg.K_g,
               "screenshot": pg.K_F1,
               "toggle_ui_visibility": pg.K_F2,
               "toggle_labels_visibility": pg.K_F3,
               "quicksave": pg.K_F4,
               "delete_body_in_editor": pg.K_DELETE
               }


sim_config = {"gc": 1.0,
              "rad_mult": 10.0,
              "coi_coef": 0.4,
              "vessel_scale": 0.1
              }


new_body_moon = {"name": "New moon",
                 "type": 0,
                 "mass": 10.0,
                 "density": 1.0,
                 "position": [0, 0],
                 "velocity": [0, 0],
                 "color": [255, 255, 255],
                 "atm_pres0": 0,
                 "atm_scale_h": 0,
                 "atm_den0": 0
                 }

new_body_planet = {"name": "New planet",
                   "type": 1,
                   "mass": 300.0,
                   "density": 1.0,
                   "position": [0, 0],
                   "velocity": [0, 0],
                   "color": [255, 255, 255],
                   "atm_pres0": 0,
                   "atm_coef": 0,
                   "atm_den": 0
                   }

new_body_gas = {"name": "New gas planet",
                "type": 2,
                "mass": 1000.0,
                "density": 0.3,
                "position": [0, 0],
                "velocity": [0, 0],
                "color": [255, 255, 255],
                "atm_pres0": 0,
                "atm_coef": 0,
                "atm_den": 0
                }

new_body_star = {"name": "New star",
                 "type": 3,
                 "mass": 6000.0,
                 "density": 1.0,
                 "position": [0, 0],
                 "velocity": [0, 0],
                 "color": [255, 255, 255],
                 "atm_pres0": 0,
                 "atm_coef": 0,
                 "atm_den": 0
                 }

new_body_bh = {"name": "New black hole",
               "type": 4,
               "mass": 500000.0,
               "density": 100.0,
               "position": [0, 0],
               "velocity": [0, 0],
               "color": [50, 50, 50],
               "atm_pres0": 0,
                "atm_coef": 0,
                "atm_den": 0
               }
