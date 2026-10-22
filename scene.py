class Scene:
    music = "menu"  # Name of the background track this scene plays
    full_width = False  # Menus are drawn on the centred canvas, and only the fishing scene uses the full width

    def __init__(self, app):
        self.app = app

    def handle_event(self, event):
        pass

    def update(self):
        pass

    def draw(self, screen):
        pass
