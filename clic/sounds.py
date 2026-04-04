"""
Sound manager for CLIC.
Typing clicks, ambient loops, UI effects via pygame.
"""

import random
from pathlib import Path

from clic.config import Config, BASE_DIR

try:
    import pygame
    import pygame.mixer
    _PYGAME = True
except ImportError:
    _PYGAME = False


class SoundManager:
    def __init__(self):
        self._ok = False
        self._typing: list = []
        self._effects: dict[str, object] = {}
        self._ambient = None
        self._ambient_on = False
        self._master_vol = 0.4
        self._typing_vol = 0.2
        self._effects_vol = 0.3
        self._ambient_vol = 0.15

    def set_volumes(self, master=None, typing=None, effects=None, ambient=None):
        if master is not None: self._master_vol = max(0.0, min(1.0, float(master)))
        if typing is not None: self._typing_vol = max(0.0, min(1.0, float(typing)))
        if effects is not None: self._effects_vol = max(0.0, min(1.0, float(effects)))
        if ambient is not None: self._ambient_vol = max(0.0, min(1.0, float(ambient)))

    def init(self):
        if not _PYGAME or not Config.get("sounds", "enabled", default=True):
            return
        try:
            pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=512)
            pygame.mixer.set_num_channels(8)
            self._ok = True
        except Exception:
            return
        self._load_typing()
        self._load_effects()
        self._load_ambient()

    def _load_typing(self):
        if not Config.get("sounds", "typing", "enabled", default=True):
            return
        d = BASE_DIR / Config.get("sounds", "typing", "directory", default="sounds/typing")
        if not d.is_dir():
            return
        for f in d.iterdir():
            if f.suffix.lower() in (".wav", ".ogg", ".mp3"):
                try:
                    self._typing.append(pygame.mixer.Sound(str(f)))
                except Exception:
                    pass

    def _load_effects(self):
        if not Config.get("sounds", "effects", "enabled", default=True):
            return
        for action, fp in Config.get("sounds", "effects", "mapping", default={}).items():
            p = BASE_DIR / fp
            if p.exists():
                try:
                    self._effects[action] = pygame.mixer.Sound(str(p))
                except Exception:
                    pass

    def _load_ambient(self):
        fp = Config.get("sounds", "ambient", "file", default="sounds/ambient/ambient.wav")
        p = BASE_DIR / fp
        if p.exists():
            try:
                self._ambient = pygame.mixer.Sound(str(p))
            except Exception:
                pass

    def play_typing(self):
        if not self._ok or not self._typing:
            return
        s = random.choice(self._typing)
        s.set_volume(self._master_vol * self._typing_vol)
        s.play()

    def play_effect(self, action: str):
        if not self._ok:
            return
        s = self._effects.get(action)
        if not s:
            return
        s.set_volume(self._master_vol * self._effects_vol)
        s.play()

    def toggle_ambient(self):
        if not self._ok or not self._ambient:
            return
        if self._ambient_on:
            self._ambient.stop()
            self._ambient_on = False
        else:
            self._ambient.set_volume(self._master_vol * self._ambient_vol)
            self._ambient.play(loops=-1)
            self._ambient_on = True

    def shutdown(self):
        if self._ok:
            pygame.mixer.quit()
            self._ok = False
