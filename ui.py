import pygame

BTN_BG = (70, 130, 180)   
BTN_HL = (100, 160, 210)  
TEXT = (255, 255, 255)   

class Buttons:
    def __init__(self, x, y, w, h, text, font, callback=None, bg_color=BTN_BG, text_color=TEXT):
        if isinstance(x, (tuple, list)) and len(x) == 4 and y is None:
            rx, ry, rw, rh = x
            x, y, w, h = rx, ry, rw, rh

        self.rect = pygame.Rect(int(x), int(y), int(w), int(h))
        self.text = text
        self.font = font
        self.bg_color = bg_color
        self.text_color = text_color
        self.callback = callback
        self.hover = False
        self.disabled = False
        self.visible = True

    def draw(self, surface):
        if not self.visible:
            return
        
        if self.disabled:
            color = (80,80,80)
        else:
            color = BTN_HL if self.hover else self.bg_color

        pygame.draw.rect(surface, color, self.rect, border_radius=10)
        pygame.draw.rect(surface, (0,0,0), self.rect, 2, border_radius=10)

        if self.font and self.text:
            text_surf = self.font.render(self.text, True, self.text_color)
            text_rect = text_surf.get_rect(center=self.rect.center)
            surface.blit(text_surf, text_rect)
    
    def handle_event(self, event):
        if not self.visible:
            return
        
        if self.disabled:
            if event.type == pygame.MOUSEMOTION:
                self.hover = False
            return
        if event.type == pygame.MOUSEMOTION:
            self.hover = self.rect.collidepoint(event.pos)
        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            if self.rect.collidepoint(event.pos):
                if callable(self.callback):
                    try:
                        self.callback()
                    except Exception as e:
                        print("Button callback error: ", e)

def create_fonts():
    MID = pygame.font.SysFont("arial", 25, bold=True)
    SMALL = pygame.font.SysFont("arial", 15)
    return MID, SMALL
