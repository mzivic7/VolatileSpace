import numpy as np
import pygame

from volatilespace import peripherals
from volatilespace.graphics import graphics

graphics = graphics.Graphics()

rng = np.random.default_rng()

# generate pool of random numbers with gaussian distribution weighted on 0
rand_color_pool = rng.normal(0, 80, 1000)
rand_color_pool = rand_color_pool[rand_color_pool >= 0]
rand_color_pool = rand_color_pool[rand_color_pool <= 255]
# generate pool of random numbers with gaussian distribution weighted on 255
rand_color_pool_inv = rng.normal(0, 80, 1000) + 255
rand_color_pool_inv = rand_color_pool_inv[rand_color_pool_inv >= 0]
rand_color_pool_inv = rand_color_pool_inv[rand_color_pool_inv <= 255]


def random_star_color(radius, speed, opacity=1):
    """Generate star color based on its radius and speed"""
    if speed < 1.5:   # slow stars
        if radius == 1:
            color = (rng.choice(rand_color_pool_inv), 255, 255)   # slow, small = white > blue
        if radius == 2:
            color = (255, 255, rng.choice(rand_color_pool_inv))   # slow, med = white > yellow
        if radius == 3:
            color = (rng.choice(rand_color_pool_inv), 255, 255)    # slow, large = white > blue
            if rng.choice([True, False], p=[0.3, 0.7]) is True:   # in 30% cases:
                color = (255, rng.choice(rand_color_pool), 0)    # slow, large = add some red
    if speed >= 1.5:   # fast stars:
        if radius == 1:
            red_fix = rng.choice(rand_color_pool)   # same value for green and blue
            color = (255, red_fix, red_fix)   # fast, small = red > white
        if radius == 2:
            color = (255, 255, rng.choice(rand_color_pool_inv))   # fast, med = white > yellow
        if radius == 3:
            color = (255, rng.integers(0, 255), 0)   # fast, large = red = yellow
    return (int(color[0]*opacity), int(color[1]*opacity), int(color[2]*opacity))


def random_cluster_stars(count_minmax, size_mult, speed, radius_prob, opacity, bg_imgs, use_img=False):
    """Generate random star position and color in cluster"""
    count = rng.integers(count_minmax[0], count_minmax[1])
    size = rng.integers(count * min(size_mult), count * max(size_mult))
    stars = np.empty((count, 4), dtype=object)   # [sx, sy, rad, col]
    stars[:, 0] = rng.normal(0, size, count)   # stars coordinates from gaussian distribution
    stars[:, 1] = rng.normal(0, size, count)
    for star in range(count):
        radius = rng.choice([1, 2, 3], p=radius_prob)
        stars[star, 2] = radius
        if use_img:
            stars[star, 3] = graphics.fill(bg_imgs[0][radius-1], random_star_color(radius, speed, opacity))
        else:
            stars[star, 3] = random_star_color(radius, speed, opacity)
    return stars


def new_pos(pos, res, frame, zoom_off, zoom):
    """Cycle stars from extended screen edge to opposite"""
    size = len(pos)
    pos[:, 0] = np.where(
        pos[:, 0] >= res[0] + frame,
        (rng.integers(-frame, 0, size=size) - zoom_off[0]) / zoom,
        pos[:, 0],
    )
    pos[:, 0] = np.where(
        pos[:, 0] <= - frame,
        (rng.integers(res[0], res[0] + frame, size=size) - zoom_off[0]) / zoom,
        pos[:, 0],
    )
    pos[:, 1] = np.where(
        pos[:, 1] >= res[1] + frame,
        (rng.integers(-frame, 0, size=size) - zoom_off[1]) / zoom,
        pos[:, 1],
    )
    pos[:, 1] = np.where(
        pos[:, 1] <= - frame,
        (rng.integers(res[1], res[1] + frame, size=size) - zoom_off[1]) / zoom,
        pos[:, 1],
    )
    return pos


class BgStars():
    """Background stars drawing and moving class"""
    def __init__(self):
        self.reload_settings()
        self.star_field = np.empty((0, 5), dtype=object)   # [x, y, radius, speed, color]
        self.clusters = np.empty((0, 4), dtype=object)   # [cx, cy, vel, [sx, sy, rad, col]]
        self.res = [0, 0]
        self.bg_imgs = [[pygame.image.load(f"images/background/{star}.png").convert_alpha() for star in radius] for radius in [[11, 12, 13], [21, 22, 23]]]
        # format: [radius, speed]

    def reload_settings(self):
        """Reload all settings, should be run every time settings are changed"""
        self.num = int(peripherals.load_settings("background", "stars_num"))   # how many stars on extended screen
        self.new_color = peripherals.load_settings("background", "stars_new_color")
        self.use_img = peripherals.load_settings("background", "use_img")
        # size of frame aded around screen to allow zooming and discreete cluster creation and remember stars that are off screen
        self.frame = int(peripherals.load_settings("background", "extra_frame"))
        self.custom_speed = float(peripherals.load_settings("background", "stars_speed_mult"))
        self.opacity = float(peripherals.load_settings("background", "stars_opacity"))
        self.cluster_enable = peripherals.load_settings("background", "cluster_enable")
        self.cluster_new = peripherals.load_settings("background", "cluster_new")
        self.cluster_num = int(peripherals.load_settings("background", "cluster_num"))
        self.cluster_stars = peripherals.load_settings("background", "cluster_star")   # min and max number of stars in cluster
        self.size_mult = peripherals.load_settings("background", "cluster_size_mult")   # cluster size min and max multiplier
        # probabilities for random star generation
        self.radius_prob = peripherals.load_settings("background", "stars_radius")   # radius (1=small)
        self.speed_prob = peripherals.load_settings("background", "stars_speed")   # speed (1=slow)
        self.zoom_min = float(peripherals.load_settings("background", "stars_zoom_min"))
        self.zoom_max = float(peripherals.load_settings("background", "stars_zoom_max"))
        self.zoom_sim_mult = float(peripherals.load_settings("background", "zoom_mult"))   # simulation zoom multiplier to get bg_zoom
        graphics.reload_settings()

        self.opacity = min(self.opacity, 1)
        self.opacity = max(self.opacity, 0)


    def set_screen(self):
        """Load pygame-related variables, this should be run after pygame has initialised or resolution has changed"""
        self.star_field = np.empty((0, 5), dtype=object)   # [x, y, radius, speed, color]
        self.clusters = np.empty((0, 4), dtype=object)   # [cx, cy, vel, [sx, sy, rad, col]]
        self.res = pygame.display.get_surface().get_size()
        graphics.set_screen()

        # generate initial star filed
        for _ in range(self.num):
            star_x = rng.integers(0, self.res[0]+self.frame*2)-self.frame
            star_y = rng.integers(0, self.res[1]+self.frame*2)-self.frame
            radius = rng.choice([1, 2, 3], p=self.radius_prob)
            speed = rng.choice([1, 2, 3], p=self.speed_prob) * radius / 2   # larger stars are faster
            if radius == 3:
                speed = np.sqrt(speed)  # decrease speed for few fast and large stars
            color = random_star_color(radius, speed, self.opacity)
            if self.use_img:   # replace color with colored image of star
                color = graphics.fill(self.bg_imgs[int(speed > 1.5)][radius-1], color)
            self.star_field = np.vstack((self.star_field, np.array([star_x, star_y, radius, speed, color], dtype=object)))

        # generate initial clusters
        for _ in range(self.cluster_num):
            cluster_x = rng.integers(-self.frame, self.res[0]+self.frame)
            cluster_y = rng.integers(-self.frame, self.res[1]+self.frame)
            cluster_speed = rng.choice([1, 2, 3], p=self.speed_prob)
            stars = random_cluster_stars(self.cluster_stars, self.size_mult, cluster_speed, self.radius_prob, self.opacity, self.bg_imgs, self.use_img)
            self.clusters = np.vstack((self.clusters, np.array([cluster_x, cluster_y, cluster_speed, stars], dtype=object)))


    def draw_bg(self, screen, speed_mult, direction, zoom_in):
        """Draw stars and clusters on screen with movement in direction, and zoom effect"""
        zoom_min_coef = np.log(self.zoom_max/self.zoom_min - 1)   # bellow eq solved for zoom_min_coef, where x=zoom_min and y=0
        zoom = self.zoom_max / (1 + np.e**(zoom_min_coef - zoom_in * self.zoom_sim_mult))   # limit zoom with logistic function: y=a/1+e^(b-x)
        zoom_off = (self.res[0] / 2 - (zoom * self.res[0] / 2), self.res[1] / 2 - (zoom * self.res[1] / 2))
        self.star_field = new_pos(self.star_field, self.res, self.frame, zoom_off, zoom)   # cycle stars at edge
        # move stars
        self.star_field[:, 0] = self.star_field[:, 0] - self.star_field[:, 3] * speed_mult * np.cos(direction) * self.custom_speed
        self.star_field[:, 1] = self.star_field[:, 1] + self.star_field[:, 3] * speed_mult * np.sin(direction) * self.custom_speed
        stars_zoom_pos = np.column_stack((self.star_field[:, 0]*zoom + zoom_off[0], self.star_field[:, 1]*zoom + zoom_off[1]))   # star position with zoom
        for num, star in enumerate(self.star_field):
            star_zoom = stars_zoom_pos[num]
            if self.new_color:
                if self.use_img:
                    star[4] = graphics.fill(self.bg_imgs[int(star[3] > 1.5)][star[2]-1], random_star_color(star[2], star[3], self.opacity))
                else:
                    star[4] = random_star_color(star[2], star[3], self.opacity)
            if star_zoom[0] >= -1 and star_zoom[1] >= -1 and star_zoom[0] <= self.res[0]+1 and star_zoom[1] <= self.res[1]+1:   # if star is on screen
                if self.use_img:
                    screen.blit(star[4], star_zoom)
                else:
                    graphics.draw_circle_fill(screen, star[4], star_zoom, star[2])   # screen, color, pos, radius

        if self.cluster_enable is True:
            self.clusters[:, 0] -= self.clusters[:, 2] * speed_mult * np.cos(direction) * self.custom_speed  # move cluster
            self.clusters[:, 1] += self.clusters[:, 2] * speed_mult * np.sin(direction) * self.custom_speed
            self.clusters = new_pos(self.clusters, self.res, self.frame, zoom_off, zoom)   # cycle stars at edge
            for cluster in self.clusters:
                if self.cluster_new:
                    cluster[3] = random_cluster_stars(self.cluster_stars, self.size_mult, cluster[2], self.radius_prob, self.opacity, self.bg_imgs, self.use_img)
                for star in cluster[3]:
                    star_zoom = ((star[0] + cluster[0]) * zoom + zoom_off[0], (star[1] + cluster[1]) * zoom + zoom_off[1])   # star position with zoom
                    if star_zoom[0] >= 0-1 and star_zoom[1] >= 0-1 and star_zoom[0] <= self.res[0]+1 and star_zoom[1] <= self.res[1]+1:
                        if self.use_img:
                            screen.blit(star[3], star_zoom)
                        else:
                            graphics.draw_circle_fill(screen, star[3], star_zoom, star[2])   # screen, color, pos, radius
