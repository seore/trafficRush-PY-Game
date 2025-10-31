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

# ===================== Game Missions =====================
class Missions:
    # "survive", "coins", "combo"
    def __init__(self, kind, target, reward):
        self.kind = kind
        self.target = target 
        self.progress = 0 
        self.completed = False 
        self.reward = reward 
        self.popup_t = 0.0

    def label(self):
        if self.kind == "survive":
            return f"Survive {self.target}s"
        if self.kind == "coins":
            return f"Collect {self.target} coins"
        if self.kind == "combo":
            return f"Near-miss combo x{self.target}"
        return "Mission"
    
    def update_progress(self, game, dt):
        if self.completed: return
        if self.kind == "survive":
            self.progress += dt
            if self.progress >= self.target: 
                self.complete(game)
        elif self.kind == "coins":
            self.progress = game.coins_collected
            if self.progress >= self.target:
                self.complete(game)
        elif self.kind == "combo":
            self.progress = max(self.progress, game.near_miss_combo)
            if self.progress >= self.target:
                self.complete(game)
    
    def complete(self, game):
        self.completed = True
        game.score += self.reward
        self.popup_t = 2.0

def generate_game_mission(difficulty):
    if difficulty == "Easy":
        return [
            Missions("survive", 30, 200), 
            Missions("coins", 10, 150), 
            Missions("combo", 3, 150),
        ]
    if difficulty == "Hard":
        return [
            Missions("survive", 60, 400), 
            Missions("coins", 20, 300), 
            Missions("combo", 6, 350),
        ]
    return [
            Missions("survive", 45, 300), 
            Missions("coins", 15, 250), 
            Missions("combo", 4, 250),
        ]


# ===================== The Game =====================
STATE_MENU, STATE_PLAY, STATE_PAUSE, STATE_SETTINGS, STATE_MISSIONS, STATE_GAMEOVER = range(6)

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

        # game missions and UI
        self.missions = generate_game_mission(self.diff)
        self.title_t = 0.0
        self.buttons = []
        self.build_menu_buttons()

        # game power-up states
        self.slow_t = 0.0     
        self.ghost_t = 0.0     
        self.magnet_t = 0.0    

        # game toggles
        self.night = False
        self.rain = False
        self.state = STATE_MENU

        # game settings
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
        return (last.y - ENEMY_HEIGHT) > SAFE_SPAWN_GAP
    
    # -------- UI Settings ------------
    def build_menu_buttons(self):
        self.buttons = []
        spacing = 68
        w, h = 260, 52
        x = (WIDTH - w)//2
        start_y = 300
        def add(label, cb):
            self.buttons.append(Button((x, start_y + spacing * len(self.buttons), w, h), label, cb))
        add("Start (1/2/3)", lambda: None)
        add("Settings", lambda: self.goto_settings())
        add("Missions", lambda: self.goto_missions())
        add("Quit", lambda: self.quit())

    def goto_settings(self):
        self.state = STATE_SETTINGS

    def goto_missions(self):
        self.state = STATE_MISSIONS

    def quit(self):
        pygame.quit(); sys.exit()

    def update_play(self, dt):
        if self.dead: return
        self.elapsed += dt
        self.speed += (self.SPEED_RAMP/60.0) * dt
        # game timers
        self.slow_t = max(0.0, self.slow_t - dt)
        self.ghost_t = max(0.0, self.ghost_t - dt)
        self.magnet_t = max(0.0, self.magnet_t - dt)

        # scores by distance 
        self.score += (self.speed * dt) / 10.0

        # spawns
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            lanes = list(range(LANES)); random.shuffle(lanes)
            cars_to_spawn = random.choice([1,2,2,3])
            spawned = 0
            for lane in lanes:
                if spawned >= cars_to_spawn: break
                if self.can_spawn_lane(lane):
                    name, vinfo = weighted_choice(VEHICLE_TYPES)
                    self.enemies.append(Enemy(lane, y=-vinfo[0][1], vtype_name=name, vinfo=vinfo))
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

        # update on game entities
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

        # coin collection
        for c in self.coins:
            if c.rect.colliderect(self.player.rect):
                c.collected = True
                self.coins_collected += 1
                self.score += 50 + 5 * self.near_miss_combo  

        # power-up collect
        for p in self.powerups:
            if p.rect.colliderect(self.player.rect):
                if p.kind == "SLOW": self.slow_t = 4.0
                elif p.kind == "GHOST": self.ghost_t = 3.0
                elif p.kind == "MAGNET": self.magnet_t = 6.0
                p.rect.y = HEIGHT + 100  

        # near-miss detection (enemy passes without hit)
        for e in self.enemies:
            if not e.near_miss_counted:
                vertical_gap = e.rect.bottom - self.player.rect.top
                same_lane = (e.lane == self.player.lane)
                if 0 < vertical_gap < 26 and same_lane:
                    e.near_miss_counted = True
                    self.near_miss_combo += 1
                    self.score += 20 + 10*self.near_miss_combo
        if random.random() < 0.01:
            self.near_miss_combo = max(0, self.near_miss_combo - 1)

        # game missions
        for m in self.missions:
            m.update_progress(self, dt)
            if m.popup_t > 0:
                m.popup_t -= dt

        # road scroll
        self.road_scroll = (self.road_scroll + self.speed*sf*dt) % (DASH_HEIGHT + DASH_GAP)

        # engine pitch (only if audio present)
        if ENGINE:
            ENGINE.set_volume(self.volume * min(1.0, 0.5 + (self.speed/400.0)))

    def draw_game_world(self, surf):
        surf.fill(BG)
        pygame.draw.rect(surf, ROAD, (ROAD_MARGIN, 0, WIDTH - 2*ROAD_MARGIN, HEIGHT))
        road_width = WIDTH - 2*ROAD_MARGIN
        lane_w = road_width / LANES
        # lane details
        for i in range(1, LANES):
            x = int(ROAD_MARGIN + lane_w * i)
            y = -int(self.road_scroll)
            while y < HEIGHT:
                pygame.draw.rect(surf, LANE_LINE, (x - LANE_LINE_WIDTH//2, y, LANE_LINE_WIDTH, DASH_HEIGHT))
                y += DASH_HEIGHT + DASH_GAP

        # rain detail overlay
        if self.rain:
            rain = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            for _ in range(90):
                rx = random.randrange(ROAD_MARGIN, WIDTH-ROAD_MARGIN)
                ry = random.randrange(0, HEIGHT)
                pygame.draw.line(rain, (180,180,220,110), (rx, ry), (rx+2, ry+10), 2)
            surf.blit(rain, (0,0))

        for c in self.coins: c.draw(surf)
        for p in self.powerups: p.draw(surf)
        self.player.draw(surf, night=self.night)
        for e in self.enemies: e.draw(surf, night=self.night)

        # nightMode global dim
        if self.night:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
            overlay.fill((0,0,0,120))
            surf.blit(overlay, (0,0))

    def draw_game_hud(self, surf):
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
        
        # game missions panel 
        panel = pygame.Surface((WIDTH//2+20, 66), pygame.SRCALPHA)
        pygame.draw.rect(panel, (30,30,45,120), panel.get_rect(), border_radius=10)
        y = 6
        for m in self.missions:
            prog = m.progress if m.kind=="survive" else min(m.progress, m.target)
            line = SMALL.render(f"{m.label()} [{int(prog)}/{int(m.target)}]{' ✓' if m.completed else ''}",
                                True, UI_ACCENT if m.completed else TEXT)
            panel.blit(line, (10, y))
            y += 20
        surf.blit(panel, ((WIDTH - panel.get_width())//2,8))

        if any(m.popup_t > 0 for m in self.missions):
            popup = pygame.Surface((WIDTH - 80, 50), pygame.SRCALPHA)
            pygame.draw.rect(popup, (40,80,40,220), popup.get_rect(), border_radius=12)
            draw_text_center(popup, "MISSION COMPLETE! +Reward added to Score", MID, (230,255,230), 10)
            surf.blit(popup, (40, HEIGHT-100))

    def draw_menu(self, surf, dt):
        self.title_t += dt
        # animated game title 
        title_y = 140 + int(8 * math.sin(self.title_t * 2.2))
        draw_text_center(surf, "TRAFFIC RUSH", BIG, UI_ACCENT, title_y)
        draw_text_center(surf, "1) Easy   2) Normal   3) Hard", MID, TEXT, title_y+60)
        draw_text_center(surf, "Game Controls: click buttons M:Night  R:Rain", SMALL, TEXT, title_y+92)
        for b in self.buttons: b.draw(surf)

    def draw_missions(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "MISSIONS", BIG, TEXT, 110)
        y = 170
        for m in self.missions:
            txt = f"• {m.label()}  — Reward: +{m.reward} score"
            draw_text_center(surf, txt, MID, UI_ACCENT if m.completed else TEXT, y)
            y += 46
        draw_text_center(surf, "Progress updates live during play.", SMALL, TEXT, y+10)
        draw_text_center(surf, "Press P to go back.", MID, TEXT, y+54)

    def draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "PAUSED", BIG, TEXT, HEIGHT//2 - 60)
        draw_text_center(surf, "Resume: P   •   Settings: S   •   Quit: Esc", MID, TEXT, HEIGHT//2)

    def draw_settings(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "SETTINGS", BIG, TEXT, 120)
        draw_text_center(surf, f"Volume: {int(self.volume*100)}%  (Up/Down)", MID, TEXT, 200)
        draw_text_center(surf, f"Night Mode: {'On' if self.night else 'Off'} (M)", MID, TEXT, 240)
        draw_text_center(surf, f"Rain: {'On' if self.rain else 'Off'} (R)", MID, TEXT, 280)
        draw_text_center(surf, f"Fullscreen: {'On' if self.fullscreen else 'Off'} (F)", MID, TEXT, 320)
        draw_text_center(surf, "Back: P", MID, TEXT, 360)

    def draw_gameover(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "CRASH!", BIG, TEXT, HEIGHT//2 - 120)
        draw_text_center(surf, f"Score: {int(self.score):,}   Best: {int(self.best):,}", MID, TEXT, HEIGHT//2 - 70)
        # game summary
        summary = [
            f"Time Survived: {int(self.elapsed)}s",
            f"Coins: {self.coins_collected}",
            f"Near-Miss Combo: x{self.near_miss_combo}",
            f"Missions Completed: {sum(1 for m in self.missions if m.completed)}/3",
        ]
        y = HEIGHT//2 - 28
        for s in summary:
            draw_text_center(surf, s, SMALL, TEXT, y); y += 22
        draw_text_center(surf, "Press R to Restart • Esc to Quit", MID, TEXT, HEIGHT//2 + 20)

    def toggle_fullscreen(self):
        global WIN, WIDTH, HEIGHT
        self.fullscreen = not self.fullscreen
        if self.fullscreen:
            WIN = pygame.display.set_mode((WIDTH, HEIGHT), pygame.FULLSCREEN)
        else:
            WIN = pygame.display.set_mode((WIDTH, HEIGHT))
        global LANE_X
        LANE_X = lane_centers()

    # -------- Game Loop -------------
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
