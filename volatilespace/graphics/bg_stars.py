import numpy as np
import pygame
from pygame import gfxdraw
from ast import literal_eval as leval

from volatilespace.graphics import graphics
from volatilespace import fileops

graphics = graphics.Graphics()



# ### ### ### ### ### ### ###
# BUG EDITOR mouse.set_pos wayland through x11 ??? search for ### BUG ###
# BUG GRAPHICS gfxdraw uses short integers
# BUG GRAPHICS weird gfxdraw aacircle line when zoom in
# BUG GRAPGICS thicknes in gfxdraw aacircle and aaline/s
# ### ### ### ### ### ### ###



###### --Random pools-- ######
# generate pool of random numbers with gaussian distribution weighted on 0
rand_color_pool = np.random.normal(0, 80, 1000)   # random pool of numbers with gaussian distribution
rand_color_pool = rand_color_pool[rand_color_pool >=0]   # limit pool to positive value
rand_color_pool = rand_color_pool[rand_color_pool <= 255]   # limit pool to value less than 255
# generate pool of random numbers with gaussian distribution weighted on 255
rand_color_pool_inv = np.random.normal(0, 80, 1000) + 255   # random pool of numbers with gaussian distribution
rand_color_pool_inv = rand_color_pool_inv[rand_color_pool_inv >=0]   # limit pool to positive value
rand_color_pool_inv = rand_color_pool_inv[rand_color_pool_inv <= 255]   # limit pool to value less than 255



###### --Functions-- ######
def random_star_color(radius, speed, opacity=1):
    """Generate star color based on its radius and speed"""
    if speed < 1.5:   # slow stars
        if radius == 1: 
            color = (np.random.choice(rand_color_pool_inv), 255, 255)   # slow, small = white > blue
        if radius == 2: 
            color = (255, 255, np.random.choice(rand_color_pool_inv))   # slow, med = white > yellow 
        if radius == 3:
            color = (np.random.choice(rand_color_pool_inv), 255, 255)    # slow, large = white > blue
            if np.random.choice([True, False], p=[0.3, 0.7]) == True:   # in 30% cases:
                color = (255, np.random.choice(rand_color_pool), 0)    # slow, large = add some red     
    if speed >= 1.5:   # fast stars:
        if radius == 1:
            red_fix = np.random.choice(rand_color_pool)   # same value for green and blue
            color = (255, red_fix, red_fix)   # fast, small = red > white
        if radius == 2:
            color = (255, 255, np.random.choice(rand_color_pool_inv))   # fast, med = white > yellow
        if radius == 3:
            color = (255, np.random.randint(0,  255), 0)   # fast, large = red = yellow
    return (int(color[0]*opacity), int(color[1]*opacity), int(color[2]*opacity))

def random_cluster_stars(count_minmax, size_mult, speed, radius_prob, opacity):
    """Generate random star position and color in cluster"""
    count = np.random.randint(count_minmax[0], count_minmax[1])   # random cluster stars
    size = np.random.randint(count * min(size_mult), count * max(size_mult))   # random cluster size
    stars = np.empty((count, 4), dtype=object)   # [sx, sy, rad, col]
    stars[:, 0] = np.random.normal(0, size, count)   # stars coordinates from gaussian distribution
    stars[:, 1] = np.random.normal(0, size, count)
    for star in range(count):
        radius = np.random.choice([1,2,3], p=radius_prob)   # random radius from prob
        stars[star, 2] = radius
        stars[star, 3] = random_star_color(radius, speed, opacity)   # color from ranfom generator
    return stars    

def new_pos(pos, res, extra, zoom_off, zoom):
    """Cycle stars from extended screen edge to opposite"""
    change = True   # position is changed
    if pos[0] >= res[0] + extra:   # if star is out of screen
        pos[0] = (np.random.randint(- extra, 0) + zoom_off[0]) / zoom   # move it to opposite side
        # and remove zoom to get real pos (not screen coordinate)
    elif pos[0] <= - extra:
        pos[0] = (np.random.randint(res[0], res[0] + extra) - zoom_off[0]*2) / zoom
    elif pos[1] >= res[1] + extra:
        pos[1] = (np.random.randint(- extra, 0) + zoom_off[1]) / zoom
    elif pos[1] <= - extra:
        pos[1] = (np.random.randint(res[1], res[1] + extra) - zoom_off[1]*2) / zoom
    else:
        change = False   # position is not changed
    return pos, change

class Bg_Stars():
    def __init__(self):
        self.antial = leval(fileops.load_settings("background", "stars_antialiasing"))   # antialiasing
        self.num = int(fileops.load_settings("background", "stars_num"))   # how many stars on extended screen
        self.new_color = leval(fileops.load_settings("background", "stars_new_color"))   # always generate new star
        # size of frame aded around screen to allow zooming and discreete cluster creation and remember stars that are off screen
        self.extra = int(fileops.load_settings("background", "extra_frame"))
        self.custom_speed = float(fileops.load_settings("background", "stars_speed_mult"))   # custom speed multiplyer
        self.opacity = float(fileops.load_settings("background", "stars_opacity"))   # star color opacity
        self.cluster_enable = leval(fileops.load_settings("background", "cluster_enable"))   # enable clusters
        self.new_cluster = leval(fileops.load_settings("background", "cluster_new"))   # always generate new cluster
        self.cluster_num = int(fileops.load_settings("background", "cluster_num"))   # number of clusters
        self.cluster_stars = fileops.load_settings("background", "cluster_star")   # min and max number of stars in cluster
        self.size_mult = fileops.load_settings("background", "cluster_size_mult")   # cluster size min and max multiplyer
        # probabilities for random star generation
        self.radius_prob = fileops.load_settings("background", "stars_radius")   # radius (1=small)
        self.speed_prob = fileops.load_settings("background", "stars_speed")   # speed (1=slow)
        self.zoom_min = float(fileops.load_settings("background", "stars_zoom_min"))   # minimum zoom 
        self.zoom_max = float(fileops.load_settings("background", "stars_zoom_max"))   # maximum zoom
        self.zoom_sim_mult = float(fileops.load_settings("background", "zoom_mult"))   # simulation zoom multiplyer to get bg_zoom
        
        self.star_field = np.empty((0,5), dtype=object)   # [x, y, radius, speed, color]
        self.clusters = np.empty((0,4), dtype=object)   # [cx, cy, vel, [sx, sy, rad, col]]
        
        if self.opacity > 1: self.opacity = 1   # limit opacity from 0 to 1
        if self.opacity < 0: self.opacity = 0
        
    
    
    ###### --Init after pygame-- ######
    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.res = pygame.display.get_surface().get_size()   # window width, window height
        self.stars_surf = pygame.Surface(self.res)   # surface for stars
        graphics.set_screen()
        
         # generate initial star filed
        for star in range(self.num):
            star_x = np.random.randint(0, self.res[0]+self.extra*2)-self.extra
            star_y = np.random.randint(0, self.res[1]+self.extra*2)-self.extra 
            radius = np.random.choice([1,2,3], p=self.radius_prob)   # random star radius from prob
            speed = np.random.choice([1,2,3], p=self.speed_prob) * radius / 2   # random star speed from prob , but larger ones are faster
            if radius == 3:  # if star is large
                speed = np.sqrt(speed)  # decrease speed for few fast and large stars
            color = random_star_color(radius, speed, self.opacity)
            self.star_field = np.vstack((self.star_field, np.array([star_x, star_y, radius, speed, color], dtype=object)))   # add star to star field
        
        # generate initial clusters
        for clusters in range(self.cluster_num):
            cluster_x = np.random.randint(-self.extra, self.res[0]+self.extra)
            cluster_y = np.random.randint(-self.extra, self.res[1]+self.extra)
            cluster_speed = np.random.choice([1,2,3], p=self.speed_prob)   # random speed from prob
            # stars in cluster:
            stars = random_cluster_stars(self.cluster_stars, self.size_mult, cluster_speed, self.radius_prob, self.opacity)
            self.clusters = np.vstack((self.clusters, np.array([cluster_x, cluster_y, cluster_speed, stars], dtype=object)))   # add cluster
    
    
    
    ###### --Draw background stars-- ######
    def draw_bg(self, screen, speed_mult, direction, zoom_in):
        """Draw stars and clusters on screen with movement in direction, and zoom effect"""
        zoom_min_coef = np.log(self.zoom_max/self.zoom_min - 1)   #bellow eq solved for zoom_min_coef, where x=zoom_min and y=0 (log is ln)
        zoom = self.zoom_max / (1 + np.e**(zoom_min_coef - zoom_in * self.zoom_sim_mult))   # limit zoom with logistic function: y=a/1+e^(b-x)
        zoom_off = (self.res[0] / 2 - (zoom * self.res[0] / 2), self.res[1] / 2 - (zoom * self.res[1] / 2))
        
        for star in self.star_field:   # for each star
            star[0] -= star[3] * speed_mult * np.cos(direction) * self.custom_speed  # move star
            star[1] += star[3] * speed_mult * np.sin(direction) * self.custom_speed
            star_zoom = (star[0]*zoom + zoom_off[0], star[1]*zoom + zoom_off[1])   # star position with zoom
            star[:2], change = new_pos(star[:2], self.res, self.extra, zoom_off, zoom)   # cycle stars at adge
            if self.new_color is True and change is True: 
                star[4] = random_star_color(star[2], star[3])
            if star_zoom[0] >= 0-1 and star_zoom[1] >= 0-1 and star_zoom[0] <= self.res[0]+1 and star_zoom[1] <= self.res[1]+1:   # if star is on screen
                graphics.draw_circle_fill(screen, star[4], star_zoom, star[2], self.antial)   # screen, color, pos, radius
        
        if self.cluster_enable is True:
            for cluster in self.clusters:
                cluster[0] -= cluster[2] * speed_mult * np.cos(direction) * self.custom_speed  # move cluster
                cluster[1] += cluster[2] * speed_mult * np.sin(direction) * self.custom_speed
                cluster[:2], change = new_pos(cluster[:2], self.res, self.extra, zoom_off, zoom)   # cycle stars at adge
                if self.new_cluster is True and change is True: 
                    cluster[3] = random_cluster_stars(self.cluster_stars, self.size_mult, cluster[2], self.radius_prob)   # gnerate new stars
                for star in cluster[3]:
                    star_zoom = ((star[0] + cluster[0]) * zoom + zoom_off[0], (star[1] + cluster[1]) * zoom + zoom_off[1])   # star position with zoom
                    if star_zoom[0] >= 0-1 and star_zoom[1] >= 0-1 and star_zoom[0] <= self.res[0]+1 and star_zoom[1] <= self.res[1]+1:
                        graphics.draw_circle_fill(screen, star[3], star_zoom, star[2], self.antial)   # screen, color, pos, radius
