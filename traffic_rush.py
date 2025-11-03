import pygame, random, sys, math, time
from ui import Buttons, create_fonts, BTN_BG, BTN_HL, TEXT
from data import load_data, save_data
from missions import MISSION_SELETS, generate_difficulty
from data import load_data as load_player_data

# ---- Settings ----
WIDTH, HEIGHT = 480, 720
FPS = 60

LANES = 6
ROAD_MARGIN = 80
LANE_LINE_WIDTH = 6
DASH_HEIGHT = 40
DASH_GAP = 30

PLAYER_WIDTH, PLAYER_HEIGHT = 40, 68
ENEMY_WIDTH, ENEMY_HEIGHT = 42, 70
COIN_SIZE = 24
PWR_SIZE = 26

DIFFS = {
    "Easy":   dict(START_SPEED=220.0, SPEED_RAMP=22.0, SPAWN=(0.9, 1.4)),
    "Normal": dict(START_SPEED=260.0, SPEED_RAMP=28.0, SPAWN=(0.7, 1.2)),
    "Hard":   dict(START_SPEED=300.0, SPEED_RAMP=34.0, SPAWN=(0.55, 1.0)),
}

# Colors
BG = (25,25,30)
ROAD = (45,45,55)
LANE_LINE = (230,230,230)
PLAYER_COLOR = (60,190,255)
ENEMY_COLOR = (250,95,95)
GOLD = (255,210,70)
PWR_COLORS = {"SLOW":(120,200,255),"GHOST":(200,200,255),"MAGNET":(180,255,180)}
DIM = (0,0,0,160)
UI_ACCENT = (120,200,255)

pygame.init()
MID, SMALL = create_fonts()

from garage import Garage

WIN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Traffic Rush")
CLOCK = pygame.time.Clock()

FONT = pygame.font.SysFont("arial", 22, bold=True)
BIG  = pygame.font.SysFont("arial", 42, bold=True)

player_data = load_player_data()

def lane_centers():
    road_w = WIDTH - 2 * ROAD_MARGIN
    lane_w = road_w / LANES
    return [int(ROAD_MARGIN + lane_w*(i+0.5)) for i in range(LANES)]
LANE_X = lane_centers()

def rect_from_center(x,y,w,h):
    return pygame.Rect(int(x-w/2), int(y-h/2), w, h)

def draw_text_center(surf, txt, font, color, y):
    t = font.render(txt, True, color)
    surf.blit(t, ((WIDTH - t.get_width())//2, y))

def clamp(v, lo, hi): return max(lo, min(hi, v))

# ---------------- Game Entities ----------------
class Car:
    def __init__(self, vehicle_id="compact"):
        self.lane = LANES//2
        self.x = LANE_X[self.lane]
        self.y = HEIGHT - 120
        self.rect = rect_from_center(self.x, self.y, PLAYER_WIDTH, PLAYER_HEIGHT)
        self.vehicle_id = vehicle_id
    def move_lane(self, delta, slippery=False):
        target = max(0, min(LANES-1, self.lane + delta))
        if slippery and random.random() < 0.18 and 0 < target < LANES-1:
            target += random.choice([-1,1])
            target = max(0, min(LANES-1, target))
        self.lane = target; self.x = LANE_X[self.lane]; self.rect.centerx = self.x
    def draw(self, surf, night=False):
        color = PLAYER_COLOR if not night else (140,200,255)
        pygame.draw.rect(surf, color, self.rect, border_radius=10)

class Enemy:
    def __init__(self, lane, y, w=ENEMY_WIDTH, h=ENEMY_HEIGHT, speed_factor=1.0):
        self.lane = lane; self.x = LANE_X[lane]; self.y = y
        self.rect = rect_from_center(self.x, self.y, w, h)
        self.speed_factor = speed_factor
        self.color = (random.randint(160,255), random.randint(40,140), random.randint(40,140))
        self.near_miss_counted = False
    def update(self, dt, speed, slow_factor=1.0):
        self.y += speed * self.speed_factor * slow_factor * dt
        self.rect.centery = int(self.y)
    def offscreen(self): return self.rect.top > HEIGHT + 40
    def draw(self, surf, night=False):
        pygame.draw.rect(surf, self.color, self.rect, border_radius=8)

class Coin:
    def __init__(self, lane, y): self.lane=lane; self.x=LANE_X[lane]; self.y=y; self.rect=rect_from_center(self.x,self.y,COIN_SIZE,COIN_SIZE); self.collected=False
    def update(self, dt, speed, slow_factor=1.0, magnet=False, player_pos=None):
        if magnet and player_pos:
            px,py = player_pos; dx,dy = px-self.rect.centerx, py-self.rect.centery
            dist = math.hypot(dx,dy)
            if dist < 160 and dist>1:
                pull=240*dt; self.rect.centerx+=int(pull*dx/dist); self.rect.centery+=int(pull*dy/dist)
        self.y += speed*slow_factor*dt; self.rect.centery = int(self.y)
    def offscreen(self): return self.rect.top > HEIGHT + 40
    def draw(self,surf): pygame.draw.circle(surf, GOLD, self.rect.center, self.rect.width//2)

class PowerUp:
    def __init__(self, kind, lane, y): self.kind=kind; self.lane=lane; self.x=LANE_X[lane]; self.y=y; self.rect=rect_from_center(self.x,self.y,PWR_SIZE,PWR_SIZE)
    def update(self,dt,speed,slow_factor=1.0): self.y += speed*slow_factor*dt; self.rect.centery=int(self.y)
    def offscreen(self): return self.rect.top > HEIGHT + 40
    def draw(self,surf): pygame.draw.rect(surf, PWR_COLORS[self.kind], self.rect, border_radius=6); surf.blit(FONT.render(self.kind[0], True, (30,30,40)), (self.rect.centerx-6,self.rect.centery-8))

# ---------------- Game Mission wrapper ----------------
class Missions:
    def __init__(self, kind, target, reward):
        self.kind = kind; self.target = target; self.progress = 0; self.completed=False; self.reward=reward; self.popup_t=0.0
    def label(self):
        if self.kind=="survive": return f"Survive {self.target}s"
        if self.kind=="coins": return f"Collect {self.target} coins"
        if self.kind=="combo": return f"Near-miss combo x{self.target}"
        return "Mission"
    def update_progress(self,game,dt):
        if self.completed: return
        if self.kind=="survive":
            self.progress+=dt
            if self.progress>=self.target: self.complete(game)
        elif self.kind=="coins":
            self.progress = game.coins_collected
            if self.progress>=self.target: self.complete(game)
        elif self.kind=="combo":
            self.progress = max(self.progress, game.near_miss_combo)
            if self.progress>=self.target: self.complete(game)
    def complete(self,game):
        self.completed=True; game.score+=self.reward; self.popup_t=2.0

# ---------------- Game States ----------------
STATE_MENU = "menu"
STATE_MISSIONS = "missions"
STATE_PLAY = "play"
STATE_PAUSE = "pause"
STATE_SETTINGS = "settings"
STATE_GARAGE = "garage"
STATE_GAMEOVER = "gameover"

class Game:
    def __init__(self):
        self.pdata = load_player_data()
        self.coins = self.pdata.get("coins", 0)
        self.xp = self.pdata.get("xp", 0)
        self.selected_vehicle = self.pdata.get("selected_vehicle", "compact")
        self.vehicles = self.pdata.get("vehicles", {})
        # gameplay
        self.set_difficulty("Normal")
        self.reset(full=True)
        # other subsystems
        self.garage = Garage(self, MID, SMALL)
       
    def set_difficulty(self, name):
        self.diff = name
        d = DIFFS[name]
        self.START_SPEED = d["START_SPEED"]
        self.SPEED_RAMP = d["SPEED_RAMP"]
        self.SPAWN_EVERY = d["SPAWN"]
    def reset(self, full=False):
        self.player = Car(self.selected_vehicle)
        self.enemies=[]; self.coins_on_road=[]; self.powerups=[]
        self.road_scroll=0.0
        self.speed = getattr(self,"START_SPEED",260.0)
        self.spawn_timer = random.uniform(*getattr(self,"SPAWN_EVERY",(0.7,1.2)))
        self.coin_timer = random.uniform(1.2,2.2)
        self.pwr_timer = random.uniform(6.0,10.0)
        self.score=0.0
        if full: self.best=0.0
        self.coins_collected=0; self.dead=False; self.elapsed=0.0; self.near_miss_combo=0
        self.missions=[]; self.title_t=0.0
        self.slow_t=self.ghost_t=self.magnet_t=0.0
        self.night=False; self.rain=False; self.fullscreen=False
        self.state = STATE_MENU
        self.volume = 0.25
        self.build_menu_buttons()
    def build_menu_buttons(self):
        self.buttons=[]
        spacing=68; w,h=260,52
        x=(WIDTH-w)//2; start_y=300
        def add(label, cb): 
            y = start_y + spacing * len(self.buttons)
            self.buttons.append(Buttons(x, y, w, h, label, MID, cb))
        add("Play Endless", lambda: self.start_endless())
        add("Missions", lambda: self.change_state(STATE_MISSIONS))
        add("Garage", lambda: self.change_state(STATE_GARAGE))
        add("Settings", lambda: self.change_state(STATE_SETTINGS))
        add("Quit", lambda: self.quit_game())
    def quit_game(self):
        pygame.quit(); sys.exit()
    def change_state(self, s): self.state = s
    def start_endless(self):
        self.missions=[]; self.reset(full=False); self.state=STATE_PLAY
    def start_mission_from_index(self, idx):
        if idx<0 or idx>=len(MISSION_SELETS): return
        m = MISSION_SELETS[idx]
        self.missions = [Missions(m.kind, m.target, m.reward)]
        self.reset(full=False)
        self.state = STATE_PLAY
    def update_play(self, dt):
        if self.dead: return
        self.elapsed += dt
        self.speed += (self.SPEED_RAMP/60.0)*dt
        # timers
        self.slow_t = max(0.0, self.slow_t - dt); self.ghost_t = max(0.0, self.ghost_t - dt); self.magnet_t = max(0.0, self.magnet_t - dt)
        self.score += (self.speed*dt)/10.0
        # spawn enemies
        self.spawn_timer -= dt
        if self.spawn_timer <= 0:
            lanes=list(range(LANES)); random.shuffle(lanes)
            cars_to_spawn = random.choice([1,2,2,3])
            spawned=0
            for lane in lanes:
                if spawned>=cars_to_spawn: break
                if self.can_spawn_lane(lane):
                    self.enemies.append(Enemy(lane, y=-ENEMY_HEIGHT, w=ENEMY_WIDTH, h=ENEMY_HEIGHT, speed_factor=random.uniform(0.85,1.2)))
                    spawned+=1
            self.spawn_timer = random.uniform(*self.SPAWN_EVERY)* max(0.55, 1.0 - self.elapsed/120.0)
        # coins & powerups spawn
        self.coin_timer -= dt
        if self.coin_timer <= 0:
            self.coins_on_road.append(Coin(random.randrange(LANES), y=-COIN_SIZE))
            self.coin_timer = random.uniform(1.2,2.2)
        self.pwr_timer -= dt
        if self.pwr_timer <= 0:
            self.powerups.append(PowerUp(random.choice(["SLOW","GHOST","MAGNET"]), random.randrange(LANES), y=-PWR_SIZE))
            self.pwr_timer = random.uniform(6.0,10.0)
        # update entities
        sf = 0.55 if self.slow_t>0 else 1.0
        for e in self.enemies: e.update(dt, self.speed, sf)
        for c in self.coins_on_road: c.update(dt, self.speed, sf, magnet=self.magnet_t>0, player_pos=self.player.rect.center)
        for p in self.powerups: p.update(dt, self.speed, sf)
        # cull offscreen
        self.enemies = [e for e in self.enemies if not e.offscreen()]
        self.coins_on_road = [c for c in self.coins_on_road if not c.offscreen() and not c.collected]
        self.powerups = [p for p in self.powerups if not p.offscreen()]
        # collisions
        if self.ghost_t <= 0:
            for e in self.enemies:
                if e.rect.colliderect(self.player.rect):
                    self.dead=True; self.state = STATE_GAMEOVER; break
        # coin collection
        for c in list(self.coins_on_road):
            if c.rect.colliderect(self.player.rect):
                c.collected=True
                self.coins_collected += 1
                self.coins += 1
                if "stats" not in self.pdata:
                    self.pdata["stats"] = {}
                self.pdata["stats"]["total_coins"] = self.pdata["stats"].get("total_coins", 0) + 1
        # powerup pickup
        for p in self.powerups:
            if p.rect.colliderect(self.player.rect):
                if p.kind=="SLOW": self.slow_t = 4.0
                elif p.kind=="GHOST": self.ghost_t = 3.0
                elif p.kind=="MAGNET": self.magnet_t = 6.0
                p.rect.y = HEIGHT + 100
        # near-miss
        for e in self.enemies:
            if not e.near_miss_counted:
                vertical_gap = e.rect.bottom - self.player.rect.top
                if 0 < vertical_gap < 26 and e.lane == self.player.lane:
                    e.near_miss_counted=True; self.near_miss_combo += 1; self.score += 20 + 10*self.near_miss_combo
        if random.random() < 0.01: self.near_miss_combo = max(0, self.near_miss_combo-1)
        # missions
        for m in self.missions:
            m.update_progress(self, dt)
            if m.popup_t > 0: m.popup_t -= dt
        # scroll
        self.road_scroll = (self.road_scroll + self.speed*sf*dt) % (DASH_HEIGHT + DASH_GAP)
    def can_spawn_lane(self, lane):
        same = [e for e in self.enemies if e.lane==lane]
        if not same: return True
        last = max(same, key=lambda e: e.y); return (last.y - ENEMY_HEIGHT) > 140

    # ---------- Draw functions ----------
    def draw_game_world(self, surf):
        surf.fill(BG)
        pygame.draw.rect(surf, ROAD, (ROAD_MARGIN, 0, WIDTH - 2*ROAD_MARGIN, HEIGHT))
        road_w = WIDTH - 2*ROAD_MARGIN; lane_w = road_w / LANES
        for i in range(1, LANES):
            x = int(ROAD_MARGIN + lane_w * i)
            y = -int(self.road_scroll)
            while y < HEIGHT:
                pygame.draw.rect(surf, LANE_LINE, (x - LANE_LINE_WIDTH//2, y, LANE_LINE_WIDTH, DASH_HEIGHT))
                y += DASH_HEIGHT + DASH_GAP
        for c in self.coins_on_road: c.draw(surf)
        for p in self.powerups: p.draw(surf)
        self.player.draw(surf, night=self.night)
        for e in self.enemies: e.draw(surf)
        if self.night:
            overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill((0,0,0,120)); surf.blit(overlay,(0,0))
    def draw_game_hud(self, surf):
        surf.blit(FONT.render(f"Score: {int(self.score):,}", True, TEXT), (16,10))
        surf.blit(FONT.render(f"Coins: {self.coins}", True, TEXT), (16,38))
        surf.blit(FONT.render(f"Combo: x{self.near_miss_combo}", True, TEXT), (16,66))
        # missions panel
        if self.missions:
            panel = pygame.Surface((WIDTH//2+20, 66), pygame.SRCALPHA); pygame.draw.rect(panel,(30,30,45,120),panel.get_rect(),border_radius=10)
            y=6
            for m in self.missions:
                prog = m.progress if m.kind=="survive" else min(m.progress,m.target)
                panel.blit(SMALL.render(f"{m.label()} [{int(prog)}/{int(m.target)}]{' ✓' if m.completed else ''}", True, UI_ACCENT if m.completed else TEXT), (10,y)); y+=20
            surf.blit(panel, ((WIDTH-panel.get_width())//2,8))
    def draw_menu(self, surf, dt):
        self.title_t += dt
        title_y = 140 + int(8*math.sin(self.title_t*2.2))
        draw_text_center(surf, "TRAFFIC RUSH", BIG, UI_ACCENT, title_y)
        draw_text_center(surf, "Press 1=Easy 2=Normal 3=Hard", SMALL, (0,0,0), HEIGHT-60)
        draw_text_center(surf, "or use buttons below • M:Night  R:Rain", SMALL, (0,0,0), HEIGHT-40)
        for b in self.buttons: b.draw(surf)
    def draw_missions(self, surf):
        surf.fill(BG)
        draw_text_center(surf, "MISSIONS", BIG, UI_ACCENT, 90)
        draw_text_center(surf, "Click a card or press 1-6 to start", SMALL, TEXT, 130)
        # draw mission cards (single column, scrollable)
        start_y = 170; gap_y = 18; card_w, card_h = WIDTH - 2*ROAD_MARGIN, 120
        view_h = HEIGHT - start_y - 60
        content_h = start_y + len(MISSION_SELETS)*(card_h+gap_y) - gap_y
        max_scroll = max(0, content_h - view_h)
        if not hasattr(self, "mission_scroll"): self.mission_scroll = 0
        self._mission_max_scroll = max_scroll
        clip = pygame.Rect(ROAD_MARGIN, start_y-8, card_w, view_h+8)
        old_clip = surf.get_clip(); surf.set_clip(clip)
        y_off = int(self.mission_scroll)

        def get_field(obj, attr, default=None):
            try:
                val = getattr(obj, attr)
                return val
            except Exception:
                pass

            try:
                return obj.get(attr, default) if isinstance(obj, dict) else default
            except Exception:
                return default
            
        for i,m in enumerate(MISSION_SELETS):
            name = get_field(m, "name", get_field(m, "title", f"Mission {i+1}"))
            desc = get_field(m, "desc", get_field(m, "description", f"No description {i+1}"))
            reward = get_field(m, "reward", 0)

            rect = pygame.Rect(ROAD_MARGIN, start_y + i*(card_h+gap_y) - y_off, card_w, card_h)
            hover = rect.collidepoint(pygame.mouse.get_pos())
            pygame.draw.rect(surf, BTN_HL if hover else BTN_BG, rect, border_radius=12)
            pygame.draw.rect(surf, (0,0,0), rect, 2, border_radius=12)
            pad_x, pad_y = 14, 10
            surf.blit(MID.render(f"{i+1}. {name}", True, TEXT), (rect.x+pad_x, rect.y+pad_y))

            desc_font = pygame.font.SysFont("arial", 16)
            lines = []
            max_chars = 46
            words = desc.split()
            line = ""

            for w in words:
                if len(line) + len(w) + 1 <= max_chars:
                    line = (line + " " + w).strip()
                else:
                    lines.append(line)
                    line = w
                if len(lines) >= 2:
                    break
                for li,ln in enumerate(lines[:2]):
                    surf.blit(desc_font.render(ln, True, (210,215,230)), (rect.x+pad_x, rect.y+pad_y+28+li*20))

            surf.blit(SMALL.render(f"Reward: +{reward} score", True, UI_ACCENT), (rect.x+pad_x, rect.bottom - 28))

        surf.set_clip(old_clip)
        draw_text_center(surf, "Use Wheel/Up/Down to scroll • Press B to go back", SMALL, (0,0,0), HEIGHT-32)

    def draw_pause(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "PAUSED", BIG, TEXT, HEIGHT//2 - 60)
        draw_text_center(surf, "Resume: P  •  Settings: S  •  Back: Esc", MID, TEXT, HEIGHT//2)
    def draw_settings(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "SETTINGS", BIG, TEXT, 120)
        draw_text_center(surf, f"Volume: {int(self.volume*100)}%  (Up/Down)", MID, TEXT, 200)
        draw_text_center(surf, f"Night Mode: {'On' if self.night else 'Off'} (M)", MID, TEXT, 240)
        draw_text_center(surf, f"Rain: {'On' if self.rain else 'Off'} (R)", MID, TEXT, 280)
        draw_text_center(surf, f"Fullscreen: {'On' if getattr(self,'fullscreen',False) else 'Off'} (F)", MID, TEXT, 320)
        draw_text_center(surf, "Back: P", MID, TEXT, 360)
    def draw_gameover(self, surf):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA); overlay.fill(DIM); surf.blit(overlay,(0,0))
        draw_text_center(surf, "CRASH!", BIG, (255,60,60), HEIGHT//2 - 120)
        draw_text_center(surf, f"Score: {int(self.score):,}   Best: {int(getattr(self,'best',0)):,}", MID, TEXT, HEIGHT//2 - 70)
        y = HEIGHT//2 - 28
        for s in [f"Time Survived: {int(self.elapsed)}s", f"Coins: {self.coins_collected}", f"Near-Miss Combo: x{self.near_miss_combo}"]:
            draw_text_center(surf, s, SMALL, TEXT, y); y+=22
        draw_text_center(surf, "Press R to Restart • Esc to Quit • G for Garage", MID, TEXT, HEIGHT//6 + 20)

    # ---------------- Main Game loop ----------------
    def main_update_draw(self):
        global WIN
        running = True
        while running:
            dt = CLOCK.tick(FPS)/1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT: running=False; break
                if event.type == pygame.MOUSEMOTION:
                    if self.state == STATE_MENU:
                        for b in self.buttons: b.handle_event(event)
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        if self.state == STATE_MENU:
                            for b in self.buttons: b.handle_event(event)
                        elif self.state == STATE_MISSIONS:
                            # click on mission cards
                            mx,my = event.pos; start_y=170; gap_y=18; card_h=120; card_w=WIDTH-2*ROAD_MARGIN
                            y_off = int(getattr(self,"mission_scroll",0))
                            for i,_ in enumerate(MISSION_SELETS):
                                r = pygame.Rect(ROAD_MARGIN, start_y + i*(card_h+gap_y)-y_off, card_w, card_h)
                                if r.collidepoint(mx,my): self.start_mission_from_index(i); break
                        elif self.state == STATE_GARAGE:
                            self.garage.click_at(event.pos)
                if event.type == pygame.MOUSEWHEEL:
                    if self.state == STATE_MISSIONS:
                        self.mission_scroll = clamp(getattr(self,"mission_scroll",0) - event.y*40, 0, getattr(self,"_mission_max_scroll",0))
                    if self.state == STATE_GARAGE:
                        self.garage.scroll_by(-event.y*40)
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        if self.state in (STATE_MISSIONS, STATE_SETTINGS, STATE_PAUSE, STATE_GARAGE): self.state = STATE_MENU
                        else: running=False; break
                    if event.key == pygame.K_m: self.night = not self.night
                    if event.key == pygame.K_r and self.state in (STATE_PLAY, STATE_PAUSE, STATE_SETTINGS, STATE_MENU, STATE_MISSIONS):
                        self.rain = not self.rain
                    if event.key == pygame.K_f: 
                        self.fullscreen = not getattr(self,'fullscreen',False)
                        WIN = pygame.display.set_mode((WIDTH,HEIGHT), pygame.FULLSCREEN if self.fullscreen else 0)
                    if self.state == STATE_MENU:
                        if event.key == pygame.K_1: self.set_difficulty("Easy"); self.start_endless()
                        if event.key == pygame.K_2: self.set_difficulty("Normal"); self.start_endless()
                        if event.key == pygame.K_3: self.set_difficulty("Hard"); self.start_endless()
                    elif self.state == STATE_PLAY:
                        if event.key in (pygame.K_a, pygame.K_LEFT): self.player.move_lane(-1, slippery=self.rain)
                        if event.key in (pygame.K_d, pygame.K_RIGHT): self.player.move_lane(+1, slippery=self.rain)
                        if event.key == pygame.K_p: self.state = STATE_PAUSE
                    elif self.state == STATE_PAUSE:
                        if event.key == pygame.K_p: self.state = STATE_PLAY
                        if event.key == pygame.K_s: self.state = STATE_SETTINGS
                    elif self.state == STATE_SETTINGS:
                        if event.key == pygame.K_p: self.state = STATE_PAUSE
                        if event.key == pygame.K_UP: self.volume = min(1.0, self.volume + 0.05)
                        if event.key == pygame.K_DOWN: self.volume = max(0.0, self.volume - 0.05)
                    elif self.state == STATE_MISSIONS:
                        if pygame.K_1 <= event.key <= pygame.K_9:
                            idx = event.key - pygame.K_1
                            if idx < len(MISSION_SELETS): self.start_mission_from_index(idx)
                        if event.key == pygame.K_UP: self.mission_scroll = clamp(getattr(self,"mission_scroll",0)-40,0,getattr(self,"_mission_max_scroll",0))
                        if event.key == pygame.K_DOWN: self.mission_scroll = clamp(getattr(self,"mission_scroll",0)+40,0,getattr(self,"_mission_max_scroll",0))
                    elif self.state == STATE_GAMEOVER:
                        if event.key == pygame.K_r:
                            self.best = max(getattr(self,'best',0), self.score)
                            self.reset(full=False)
                            self.state = STATE_MENU
                        if event.key == pygame.K_g:
                            self.state = STATE_GARAGE

            # Update & draw game screens
            if self.state == STATE_MENU:
                self.draw_game_world(WIN); self.draw_menu(WIN, dt)
            elif self.state == STATE_MISSIONS:
                self.draw_game_world(WIN); self.draw_missions(WIN)
            elif self.state == STATE_PLAY:
                self.update_play(dt); self.draw_game_world(WIN); self.draw_game_hud(WIN)
                if self.dead: self.draw_gameover(WIN)
            elif self.state == STATE_PAUSE:
                self.draw_game_world(WIN); self.draw_game_hud(WIN); self.draw_pause(WIN)
            elif self.state == STATE_SETTINGS:
                self.draw_game_world(WIN); self.draw_game_hud(WIN); self.draw_settings(WIN)
            elif self.state == STATE_GARAGE:
                self.garage.draw(WIN)
            elif self.state == STATE_GAMEOVER:
                self.draw_game_world(WIN); self.draw_game_hud(WIN); self.draw_gameover(WIN)

            pygame.display.flip()
        pygame.quit(); sys.exit()

# ---- Run ----
def main():
    Game().main_update_draw()

if __name__ == "__main__":
    main()
