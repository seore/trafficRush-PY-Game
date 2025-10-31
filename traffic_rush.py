import pygame, random, sys, math, time

WIDTH, HEIGHT = 480, 720
FPS = 60

LANES = 6
ROAD_MARGIN = 80
LANE_LINE_WIDTH = 6
DASH_HEIGHT = 40
DASH_GAP = 30

PLAYER_WIDTH, PLAYER_HEIGHT = 45, 70
ENEMY_WIDTH, ENEMY_HEIGHT = 56, 98
COIN_SIZE = 5
PWR_SIZE = 10

# Difficulty presets
DIFFS = {
    "Easy":   dict(START_SPEED=220.0, SPEED_RAMP=22.0, SPAWN=(0.9, 1.4)),
    "Normal": dict(START_SPEED=260.0, SPEED_RAMP=28.0, SPAWN=(0.7, 1.2)),
    "Hard":   dict(START_SPEED=300.0, SPEED_RAMP=34.0, SPAWN=(0.55, 1.0)),
}

# Vehicle Options
VEHICLE_TYPES = {
    "car": ((ENEMY_WIDTH, ENEMY_HEIGHT), 1.00, 55),
    "van": ((ENEMY_WIDTH + 8, ENEMY_HEIGHT + 10), 0.95, 22),
    "truck": ((ENEMY_WIDTH + 14, ENEMY_HEIGHT + 10), 0.85, 14),
    "motorcycle": ((ENEMY_WIDTH - 18, ENEMY_HEIGHT - 30), 1.18, 9)
}

SAFE_SPAWN_GAP = 140
COIN_SPAWN_EVERY = (1.2, 2.2)
PWR_SPAWN_EVERY  = (6.0, 10.0)

BG = (25, 25, 30)
ROAD = (45, 45, 55)
LANE_LINE = (230, 230, 230)
PLAYER_COLOR = (60, 190, 255)
ENEMY_COLOR = (250, 95, 95)
TEXT = (245, 245, 250)
GOLD = (255, 210, 70)
PWR_COLORS = {
    "SLOW": (120, 200, 255),
    "GHOST": (200, 200, 255),
    "MAGNET": (180, 255, 180)
}
DIM = (0,0,0,160)

UI_ACCENT = (120, 200, 255)
BTN_BG = (60, 65, 80)
BTN_HL = (90, 100, 125)

pygame.init()
FLAGS = 0
WIN = pygame.display.set_mode((WIDTH, HEIGHT), FLAGS)
pygame.display.set_caption("Traffic Rush v2")
CLOCK = pygame.time.Clock()
FONT = pygame.font.SysFont("arial", 22, bold=True)
BIG  = pygame.font.SysFont("arial", 42, bold=True)
MID  = pygame.font.SysFont("arial", 25, bold=True)
SMALL = pygame.font.SysFont("arial", 18, bold=True)

# Game Audio 
AUDIO_OK = True
try:
    pygame.mixer.init()
except Exception:
    AUDIO_OK = False

ENGINE = None
CRASH = None
if AUDIO_OK:
    try:
        # Placeholders: load your own "engine.ogg" and "crash.ogg" if available.
        # If files are missing, we silently skip.
        ENGINE = pygame.mixer.Sound("engine.ogg")
        ENGINE.play(loops=-1)
        ENGINE.set_volume(0.25)
    except Exception:
        ENGINE = None
    try:
        CRASH = pygame.mixer.Sound("crash.ogg")
    except Exception:
        CRASH = None

def lane_centers():
    road_w = WIDTH - 2*ROAD_MARGIN
    lane_w = road_w / LANES
    return [int(ROAD_MARGIN + lane_w*(i+0.5)) for i in range(LANES)]
LANE_X = lane_centers()

def rect_from_center(x, y, w, h):
    return pygame.Rect(int(x - w/2), int(y - h/2), w, h)

def draw_text_center(surf, txt, font, color, y):
    t = font.render(txt, True, color)
    surf.blit(t, ((WIDTH - t.get_width())//2, y))

def weighted_choice(d):
    items = list(d.items())
    weights = [v[2] for _, v in items]
    total = sum(weights)
    r = random.uniform(0, total)
    upto = 0
    for (name, val), w in zip(items, weights):
        if upto + w >= r:
            return name, val
        upto += w
    return items[-1]

# In-Game UI
class Button:
    def __init__(self, rect, label, cb):
        self.rect = pygame.Rect(rect)
        self.label = label
        self.cb = cb
        self.hover = False

    def draw(self, surf):
        bg = BTN_HL if self.hover else BTN_BG
        pygame.draw.rect(surf, bg, self.rect, border_radius=12)
        pygame.draw.rect(surf, (0,0,0), self.rect, 2, border_radius=12)
        t = MID.render(self.render, True, TEXT)
        surf.blit(t, (self.rect.centerx - t.get_width()//2, self.rect.centery - t.get_height()//2))

    def handle(self, ev):
        if ev.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(ev.pos)
        elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1 and self.hover:
            if self.cb: self.cb()

class Car:
    def __init__(self):
        self.lane = LANES // 2
        self.x = LANE_X[self.lane]
        self.y = HEIGHT - 120
        self.rect = rect_from_center(self.x, self.y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.lane_changes = 0

    def move_lane(self, delta, slippery=False):
        target = max(0, min(LANES-1, self.lane + delta))
        # Slippery adds a chance we overshoot by 1 lane (fun!)
        if slippery and random.random() < 0.18 and 0 < target < LANES-1:
            target += random.choice([-1, 1])
            target = max(0, min(LANES-1, target))
        if target != self.lane:
            self.lane_changes += 1
        self.lane = target
        self.x = LANE_X[self.lane]
        self.rect.centerx = self.x

    def draw(self, surf, night=False):
        color = PLAYER_COLOR if not night else (140, 200, 255)
        pygame.draw.rect(surf, color, self.rect, border_radius=10)
        w = self.rect.copy(); w.height = int(PLAYER_HEIGHT*0.25); w.y += 10
        pygame.draw.rect(surf, (200, 240, 255), w, border_radius=8)
        # Car headlights (nightMode)
        if night:
            cone = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            cx, cy = self.rect.centerx, self.rect.top+10
            for r, a in [(180, 28), (140, 38), (100, 52)]:
                pygame.draw.polygon(
                    cone, (255,255,220,a),
                    [(cx-18, cy), (cx+18, cy), (cx+60, cy - r), (cx-60, cy - r)]
                )
            surf.blit(cone, (0,0))

class Enemy:
    def __init__(self, lane, y, vtype_name, vinfo):
        self.kind = vtype_name
        (w, h), self.speed_factor, _ = vinfo
        self.lane = lane
        self.x = LANE_X[lane]
        self.y = y
        self.rect = rect_from_center(self.x, self.y, w, h)
        base = ENEMY_COLOR
        jitter = lambda c: max(0, min(255, c + random.randint(-18,18)))
        self.color = (jitter(base[0]), jitter(base[1]), jitter(base[2]))
        self.near_miss_counted = False

    def update(self, dt, base_speed, slow_factor=1.0):
        self.y += base_speed * self.speed_factor * slow_factor * dt
        self.rect.centery = int(self.y)

    def offscreen(self):
        return self.rect.top > HEIGHT + 40

    def draw(self, surf, night=False):
        c = self.color if not night else tuple(min(255, x+40) for x in self.color)
        pygame.draw.rect(surf, c, self.rect, border_radius=10)
        tl = pygame.Rect(self.rect.left + 8, self.rect.bottom - 16, 12, 12)
        tr = pygame.Rect(self.rect.right - 20, self.rect.bottom - 16, 12, 12)
        pygame.draw.rect(surf, (255, 50, 50), tl); pygame.draw.rect(surf, (255, 50, 50), tr)

class Coin:
    def __init__(self, lane, y):
        self.lane = lane
        self.x = LANE_X[lane]
        self.y = y
        self.rect = rect_from_center(self.x, self.y, COIN_SIZE, COIN_SIZE)
        self.collected = False

    def update(self, dt, speed, slow_factor=1.0, magnet=False, player_pos=None):
        if magnet and player_pos is not None:
            px, py = player_pos
            dx, dy = px - self.rect.centerx, py - self.rect.centery
            dist = math.hypot(dx, dy)
            if dist < 160 and dist > 1:
                pull = 240 * dt
                self.rect.centerx += int(pull * dx / dist)
                self.rect.centery += int(pull * dy / dist)
        self.y += speed * slow_factor * dt
        self.rect.centery = int(self.y)

    def offscreen(self):
        return self.rect.top > HEIGHT + 40

    def draw(self, surf):
        pygame.draw.circle(surf, GOLD, self.rect.center, self.rect.width//2)
        pygame.draw.circle(surf, (255,235,140), self.rect.center, self.rect.width//2 - 5, 2)

class PowerUp:
    # "SLOW", "GHOST", "MAGNET"
    def __init__(self, kind, lane, y):
        self.kind = kind
        self.lane = lane
        self.x = LANE_X[lane]
        self.y = y
        self.rect = rect_from_center(self.x, self.y, PWR_SIZE, PWR_SIZE)

    def update(self, dt, speed, slow_factor=1.0):
        self.y += speed * slow_factor * dt
        self.rect.centery = int(self.y)

    def offscreen(self):
        return self.rect.top > HEIGHT + 40

    def draw(self, surf):
        c = PWR_COLORS[self.kind]
        pygame.draw.rect(surf, c, self.rect, border_radius=8)
        t = FONT.render(self.kind[0], True, (40,40,60))
        surf.blit(t, (self.rect.centerx - t.get_width()//2, self.rect.centery - t.get_height()//2))

# ===================== The Game =====================
STATE_MENU, STATE_PLAY, STATE_PAUSE, STATE_SETTINGS, STATE_GAMEOVER = range(5)

class Game:
    def __init__(self):
        self.set_difficulty("Normal")
        self.reset(full=True)

    def set_difficulty(self, name):
        self.diff = name
        d = DIFFS[name]
        self.START_SPEED = d["START_SPEED"]
        self.SPEED_RAMP = d["SPEED_RAMP"]
        self.SPAWN_EVERY = d["SPAWN"]

    def reset(self, full=False):
        self.player = Car()
        self.enemies = []
        self.coins = []
        self.powerups = []
        self.road_scroll = 0.0
        self.speed = self.START_SPEED
        self.spawn_timer = random.uniform(*self.SPAWN_EVERY)
        self.coin_timer = random.uniform(*COIN_SPAWN_EVERY)
        self.pwr_timer  = random.uniform(*PWR_SPAWN_EVERY)
        self.score = 0.0
        if full: self.best = 0.0
        self.coins_collected = 0
        self.dead = False
        self.elapsed = 0.0
        self.near_miss_combo = 0
        # power-up states
        self.slow_t = 0.0      # slow-motion time left
        self.ghost_t = 0.0     # ghost time left (no collisions)
        self.magnet_t = 0.0    # magnet time left
        # toggles
        self.night = False
        self.rain = False
        self.state = STATE_MENU
        # settings
        self.volume = 0.25
        self.update_volume()

    def update_volume(self):
        if ENGINE: ENGINE.set_volume(self.volume)

    def slow_factor(self):
        return 0.55 if self.slow_t > 0 else 1.0

    def magnet_on(self):
        return self.magnet_t > 0

    def ghost_on(self):
        return self.ghost_t > 0

    def can_spawn_lane(self, lane):
        same = [e for e in self.enemies if e.lane == lane]
        if not same: return True
        last = max(same, key=lambda e: e.y)
        return (last.y - ENEMY_H) > SAFE_SPAWN_GAP

    def update_play(self, dt, left_pressed, right_pressed):
        if self.dead: return
        self.elapsed += dt
        self.speed += (self.SPEED_RAMP/60.0) * dt
        # timers
        self.slow_t = max(0.0, self.slow_t - dt)
        self.ghost_t = max(0.0, self.ghost_t - dt)
        self.magnet_t = max(0.0, self.magnet_t - dt)

        # score by distance + coins (handled on collect)
        self.score += (self.speed * dt) / 10.0

        # spawns
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            lanes = list(range(LANES)); random.shuffle(lanes)
            cars_to_spawn = 2 if random.random() < 0.35 else 1
            spawned = 0
            for lane in lanes:
                if spawned >= cars_to_spawn: break
                if self.can_spawn_lane(lane):
                    self.enemies.append(Enemy(lane, y=-ENEMY_H))
                    spawned += 1
            self.spawn_timer = random.uniform(*self.SPAWN_EVERY) * max(0.55, 1.0 - self.elapsed / 120.0)

        self.coin_timer -= dt
        if self.coin_timer <= 0:
            lane = random.randrange(LANES)
            self.coins.append(Coin(lane, y=-COIN_SIZE))
            self.coin_timer = random.uniform(*COIN_SPAWN_EVERY)

        self.pwr_timer -= dt
        if self.pwr_timer <= 0:
            lane = random.randrange(LANES)
            kind = random.choice(["SLOW","GHOST","MAGNET"])
            self.powerups.append(PowerUp(kind, lane, y=-PWR_SIZE))
            self.pwr_timer = random.uniform(*PWR_SPAWN_EVERY)

        # update entities
        sf = self.slow_factor()
        for e in self.enemies: e.update(dt, self.speed, sf)
        for c in self.coins:
            c.update(dt, self.speed, sf, magnet=self.magnet_on(), player_pos=self.player.rect.center)
        for p in self.powerups: p.update(dt, self.speed, sf)

        self.enemies = [e for e in self.enemies if not e.offscreen()]
        self.coins = [c for c in self.coins if not c.offscreen() and not c.collected]
        self.powerups = [p for p in self.powerups if not p.offscreen()]

        # collisions (unless ghost)
        if not self.ghost_on():
            for e in self.enemies:
                if e.rect.colliderect(self.player.rect):
                    self.dead = True
                    if CRASH: CRASH.play()
                    self.state = STATE_GAMEOVER
                    break

        # coin collect
        for c in self.coins:
            if c.rect.colliderect(self.player.rect):
                c.collected = True
                self.coins_collected += 1
                self.score += 50 + 5*self.near_miss_combo  # small combo synergy

        # power-up collect
        for p in self.powerups:
            if p.rect.colliderect(self.player.rect):
                if p.kind == "SLOW": self.slow_t = 4.0
                elif p.kind == "GHOST": self.ghost_t = 3.0
                elif p.kind == "MAGNET": self.magnet_t = 6.0
                p.rect.y = HEIGHT + 100  # remove next cull

        # near-miss detection (enemy passes close without hit)
        for e in self.enemies:
            if not e.near_miss_counted:
                # trigger when enemy bottom just passes player top within a slim delta horizontally
                vertical_gap = e.rect.bottom - self.player.rect.top
                same_lane = (e.lane == self.player.lane)
                if 0 < vertical_gap < 26 and same_lane:
                    e.near_miss_counted = True
                    self.near_miss_combo += 1
                    self.score += 20 + 10*self.near_miss_combo
        # decay combo slowly when no near misses for a while (approx via speed)
        if random.random() < 0.01:
            self.near_miss_combo = max(0, self.near_miss_combo - 1)

        # road scroll
        self.road_scroll = (self.road_scroll + self.speed*sf*dt) % (DASH_HEIGHT + DASH_GAP)

        # engine pitch (if audio present)
        if ENGINE:
            # pygame doesn’t have native pitch; emulate via volume for now
            ENGINE.set_volume(self.volume * min(1.0, 0.5 + (self.speed/400.0)))

    def draw_world(self, surf):
        # background + road
        surf.fill(BG)
        pygame.draw.rect(surf, ROAD, (ROAD_MARGIN, 0, WIDTH - 2*ROAD_MARGIN, HEIGHT))
        road_width = WIDTH - 2*ROAD_MARGIN
        lane_w = road_width / LANES
        # lane dashes
        for i in range(1, LANES):
            x = int(ROAD_MARGIN + lane_w * i)
            y = -int(self.road_scroll)
            while y < HEIGHT:
                pygame.draw.rect(surf, LANE_LINE, (x - LANE_LINE_WIDTH//2, y, LANE_LINE_WIDTH, DASH_HEIGHT))
                y += DASH_HEIGHT + DASH_GAP

        # rain overlay
        if self.rain:
            rain = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for _ in range(90):
                rx = random.randrange(ROAD_MARGIN, WIDTH-ROAD_MARGIN)
                ry = random.randrange(0, HEIGHT)
                pygame.draw.line(rain, (180,180,220,110), (rx, ry), (rx+2, ry+10), 2)
            surf.blit(rain, (0,0))

        # entities
        for c in self.coins: c.draw(surf)
        for p in self.powerups: p.draw(surf)
        self.player.draw(surf, night=self.night)
        for e in self.enemies: e.draw(surf, night=self.night)

        # night global dim
        if self.night:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,120))
            surf.blit(overlay, (0,0))

    def draw_hud(self, surf):
        # meters
        score_txt = FONT.render(f"Score: {int(self.score):,}", True, TEXT)
        best_txt = FONT.render(f"Best: {int(getattr(self,'best',0)):,}", True, TEXT)
        speed_txt = FONT.render(f"{int(self.speed)} km/h", True, TEXT)
        coins_txt = FONT.render(f"Coins: {self.coins_collected}", True, TEXT)
        combo_txt = FONT.render(f"Combo: x{self.near_miss_combo}", True, TEXT)
        surf.blit(score_txt, (16, 10))
        surf.blit(best_txt, (16, 38))
        surf.blit(coins_txt, (16, 66))
        surf.blit(combo_txt, (16, 94))
        surf.blit(speed_txt, (WIDTH - speed_txt.get_width() - 16, 10))

        # power-up timers
        px = WIDTH - 16
        for name, t in [("S", self.slow_t), ("G", self.ghost_t), ("M", self.magnet_t)]:
            if t > 0:
                bar_w, bar_h = 90, 10
                x = px - bar_w; y = 46 if name=="S" else (62 if name=="G" else 78)
                pygame.draw.rect(surf, (80,80,100), (x, y, bar_w, bar_h), border_radius=6)
                pct = min(1.0, t / (4.0 if name=="S" else (3.0 if name=="G" else 6.0)))
                pygame.draw.rect(surf, (180,220,255) if name=="S" else (220,220,255) if name=="G" else (200,255,200),
                                 (x, y, int(bar_w*pct), bar_h), border_radius=6)
                tlabel = FONT.render(name, True, TEXT)
                surf.blit(tlabel, (x-22, y-4))

    def draw_menu(self, surf):
        draw_text_center(surf, "TRAFFIC RUSH", BIG, TEXT, 160)
        draw_text_center(surf, "1) Easy   2) Normal   3) Hard", MID, TEXT, 240)
        draw_text_center(surf, "Controls: A/Left  D/Right  P:Pause  M:Night  R:Rain", FONT, TEXT, 300)
        draw_text_center(surf, "Collect coins • Power-ups: Slow, Ghost, Magnet", FONT, TEXT, 330)
        draw_text_center(surf, "Press 1/2/3 to start", FONT, TEXT, 380)

    def draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "PAUSED", BIG, TEXT, HEIGHT//2 - 60)
        draw_text_center(surf, "Resume: P   •   Settings: S   •   Quit: Esc", MID, TEXT, HEIGHT//2)

    def draw_settings(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "SETTINGS", BIG, TEXT, 140)
        draw_text_center(surf, f"Volume: {int(self.volume*100)}%  (Up/Down to change)", MID, TEXT, 210)
        draw_text_center(surf, "Night Mode: M", MID, TEXT, 260)
        draw_text_center(surf, "Rain: R", MID, TEXT, 300)
        draw_text_center(surf, "Back: P", MID, TEXT, 360)

    def draw_gameover(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "CRASH!", BIG, TEXT, HEIGHT//2 - 90)
        draw_text_center(surf, f"Score: {int(self.score):,}   Best: {int(self.best):,}", MID, TEXT, HEIGHT//2 - 30)
        draw_text_center(surf, "Press R to Restart • Esc to Quit", MID, TEXT, HEIGHT//2 + 20)

    def handle_keydown_global(self, key):
        if key == pygame.K_m: self.night = not self.night
        if key == pygame.K_r and self.state in (STATE_PLAY, STATE_PAUSE, STATE_SETTINGS):
            self.rain = not self.rain

    def main_update_draw(self):
        left_pressed = right_pressed = False
        running = True
        while running:
            dt = CLOCK.tick(FPS)/1000.0

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    self.handle_keydown_global(event.key)
                    # State transitions
                    if self.state == STATE_MENU:
                        if event.key == pygame.K_1: self.set_difficulty("Easy"); self.state = STATE_PLAY
                        if event.key == pygame.K_2: self.set_difficulty("Normal"); self.state = STATE_PLAY
                        if event.key == pygame.K_3: self.set_difficulty("Hard"); self.state = STATE_PLAY
                    elif self.state == STATE_PLAY:
                        if event.key in (pygame.K_a, pygame.K_LEFT):
                            self.player.move_lane(-1, slippery=self.rain)
                        if event.key in (pygame.K_d, pygame.K_RIGHT):
                            self.player.move_lane(+1, slippery=self.rain)
                        if event.key == pygame.K_p:
                            self.state = STATE_PAUSE
                    elif self.state == STATE_PAUSE:
                        if event.key == pygame.K_p:
                            self.state = STATE_PLAY
                        if event.key == pygame.K_s:
                            self.state = STATE_SETTINGS
                    elif self.state == STATE_SETTINGS:
                        if event.key == pygame.K_p:
                            self.state = STATE_PAUSE
                        if event.key == pygame.K_UP:
                            self.volume = min(1.0, self.volume + 0.05); self.update_volume()
                        if event.key == pygame.K_DOWN:
                            self.volume = max(0.0, self.volume - 0.05); self.update_volume()
                    elif self.state == STATE_GAMEOVER:
                        if event.key == pygame.K_r:
                            self.best = max(getattr(self,'best',0), self.score)
                            self.set_difficulty(self.diff)
                            self.reset(full=False)
                            self.state = STATE_MENU

            # Update & draw per state
            if self.state == STATE_MENU:
                self.draw_world(WIN)
                self.draw_menu(WIN)
            elif self.state == STATE_PLAY:
                self.update_play(dt, left_pressed, right_pressed)
                self.draw_world(WIN)
                self.draw_hud(WIN)
                if self.dead:
                    self.best = max(getattr(self,'best',0), self.score)
                    self.draw_gameover(WIN)
            elif self.state == STATE_PAUSE:
                self.draw_world(WIN); self.draw_hud(WIN); self.draw_pause(WIN)
            elif self.state == STATE_SETTINGS:
                self.draw_world(WIN); self.draw_hud(WIN); self.draw_settings(WIN)
            elif self.state == STATE_GAMEOVER:
                self.draw_world(WIN); self.draw_hud(WIN); self.draw_gameover(WIN)

            pygame.display.flip()

        pygame.quit(); sys.exit()

# ===================== Run =====================
def main():
    Game().main_update_draw()

if __name__ == "__main__":
    main()
