import pygame as pg


settings = {"first_run": "True",
            "resolution": [1366, 768],
            "fullscreen": "True",
            "vsync": "True",
            "curve_points": 100,
            "grid_spacing_min": 100,
            "grid_spacing_max": 200,
            "mouse_wrap": "True",
            "antialiasing": "True",
            "stars_antialiasing": "False",
            "stars_num": 500,
            "stars_new_color": "False",
            "extra_frame": 1000,
            "stars_speed_mult": 1,
            "stars_opacity": 0.7,
            "cluster_enable": "True",
            "cluster_new": "False",
            "cluster_num": 7,
            "cluster_star": [10, 40],
            "cluster_size_mult": [2, 4],
            "stars_radius": [0.6, 0.3, 0.1],
            "stars_speed": [0.5, 0.3, 0.2],
            "stars_zoom_min": 0.5,
            "stars_zoom_max": 2,
            "zoom_mult": 5,
            "stars": "True"
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
               "follow_selected_body": pg.K_f,
               "toggle_background_grid": pg.K_g,
               "cycle_grid_modes": pg.K_v,
               "screenshot": pg.K_F1,
               "toggle_ui_visibility": pg.K_F2,
               "toggle_labels_visibility": pg.K_F3
               }


sim_config = {"gc": 1.0,
              "rad_mult": 10.0
              }
