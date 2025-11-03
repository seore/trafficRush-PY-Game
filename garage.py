import pygame
from ui import Buttons, BTN_BG, BTN_HL, TEXT
from data import load_data, save_data

PANEL_BG = (40,40,50)
UNLOCK_PRICE = 100
UPGRADE_PRICE_BASE = 100

class Garage:
    def __init__(self, game, mid_font, small_font):
        self.game = game  
        self.data = load_data()
        self.vehicles = self.data["vehicles"]
        self.names = list(self.vehicles.keys())
        if self.data.get("selected_vehicle") not in self.names:
            self.data["selected_vehicle"] = self.names[0]
        self.index = self.names.index(self.data["selected_vehicle"])
        self.mid_font = mid_font 
        self.small_font = small_font
        self.buttons = [
            Buttons(100, 100, 200, 50, "Upgrade", self.mid_font),
            Buttons(100, 200, 200, 50, "Back", self.small_font),
        ]
        self.scroll = 0

    def draw(self, surf):
        surf.fill(PANEL_BG)
        def draw_centered(t, y, f=None, c=TEXT):
            font_to_use = f if f is not None else self.mid_font
            if font_to_use is None:
                font_to_use = pygame.font.SysFont("arial", 18)
            surf.blit(font_to_use.render(t, True, c), ((surf.get_width() - font_to_use.size(t)[0]) // 2, y))
        draw_centered("GARAGE", 30, None, TEXT)
        
        # coin display
        coin_text = f"Coins: {self.game.coins}"
        sf = self.small_font or pygame.font.SysFont("arial", 16)
        surf.blit(sf.render(coin_text, True, (255,215,0)), (16, 18))

        # vehicle list (single column)
        start_y = 120
        gap = 140
        for i, name in enumerate(self.names):
            y = start_y + i*gap - self.scroll
            rect = pygame.Rect(60, y, surf.get_width()-120, 110)
            pygame.draw.rect(surf, BTN_HL if i==self.index else BTN_BG, rect, border_radius=12)
            pygame.draw.rect(surf, (0,0,0), rect, 2, border_radius=12)
            
            # title
            mf = self.mid_font or pygame.font.SysFont("arial", 20, bold=True)
            surf.blit(mf.render(name.upper(), True, TEXT), (rect.x+14, rect.y+8))
           
            # stats
            v = self.vehicles[name]
            stat_line = f"ACC {v['acceleration']}  |  SPD {v['speed']}  |  MAG {v['magnet']}  |  DUR {v['duration']}"
            sf2 = self.small_font or pygame.font.SysFont("arial", 16)
            surf.blit(sf2.render(stat_line, True, (220,220,220)), (rect.x+14, rect.y+44))
            
            # buttons
            btn_rect = pygame.Rect(rect.right-140, rect.bottom-36, 120, 28)
            if v["unlocked"]:
                pygame.draw.rect(surf, (70,200,70), btn_rect, border_radius=6)
                surf.blit(sf2.render("Select", True, (0,0,0)), (btn_rect.centerx-20, btn_rect.centery-9))
            else:
                pygame.draw.rect(surf, (200,70,70), btn_rect, border_radius=6)
                surf.blit(sf2.render(f"Buy ({UNLOCK_PRICE})", True, (0,0,0)), (btn_rect.centerx-36, btn_rect.centery-9))

        # game instructions
        surf.blit(sf2.render("Click green to select, red to buy. Use Up/Down to scroll. Esc to return.", True, (200,200,200)), (24, surf.get_height()-36))

    def click_at(self, pos):
        x,y = pos
        start_y = 120
        gap = 140
        for i, name in enumerate(self.names):
            rect = pygame.Rect(60, start_y + i*gap - self.scroll, 360, 110)
            btn_rect = pygame.Rect(rect.right-140, rect.bottom-36, 120, 28)
            if btn_rect.collidepoint(x,y):
                vehicle = self.vehicles[name]
                if vehicle["unlocked"]:
                    self.data["selected_vehicle"] = name
                    self.game.selected_vehicle = name
                else:
                    # in-game purchases
                    if self.game.coins >= UNLOCK_PRICE:
                        self.game.coins -= UNLOCK_PRICE
                        vehicle["unlocked"] = True
                        self.save()
                return

    def upgrade(self, name, stat):
        vehicle = self.vehicles.get(name)
        if not vehicle: return False
        cost = UPGRADE_PRICE_BASE * (vehicle[stat] + 1)
        if self.game.coins >= cost:
            self.game.coins -= cost
            vehicle[stat] += 1
            self.save()
            return True
        return False

    def scroll_by(self, dy):
        self.scroll = max(0, self.scroll + dy)

    def save(self):
        self.data["coins"] = self.game.coins
        self.data["selected_vehicle"] = self.game.selected_vehicle
        save_data(self.data)
