import pygame
from trackable import *
from gui import ObserverApp

WIDTH, HEIGHT = 800, 700
gravity = 0.1


class Player:
    def __init__(self):
        self.x = 0.0
        self.y = 0.0
        self.dx = 0.0
        self.dy = 0.0
        self.ddx = 0.0
        self.ddy = 0.0

    def move(self):
        self.x += self.dx
        self.y += self.dy
        if self.x < 0:
            self.x = 0
            self.dx = -self.dx
        if self.x > WIDTH - 50:
            self.x = WIDTH - 50
            self.dx = -self.dx
        if self.y < 0:
            self.y = 0
            self.dy = -self.dy
        if self.y > HEIGHT - 50:
            self.y = HEIGHT - 50
            self.dy = -self.dy

        if abs(self.dx) > 10:
            self.dx = 10 if self.dx > 0 else -10

        if abs(self.dy) > 10:
            self.dy = 10 if self.dy > 0 else -10



    def draw(self, screen):
        pygame.draw.rect(screen, (255, 0, 0), (self.x, self.y, 50, 50))

    def update(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.dx = -1
        if keys[pygame.K_RIGHT]:
            self.dx = 1
        if keys[pygame.K_UP]:
            self.dy = -1
        if keys[pygame.K_DOWN]:
            self.dy = 1

        self.dx += self.ddx
        self.dy += self.ddy
        self.move()




def initialise_gui():
    def run_gui(observer):
        import tkinter as tk
        root = tk.Tk()
        app = ObserverApp(observer, master=root)
        app.pack()
        root.mainloop()

    mediator = Mediator()
    o = Observer(mediator)
    threading.Thread(target=run_gui, args=(o,)).start()
    return mediator

import time
@track_vars("paused")
def main():

    start_logging()
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    clock = pygame.time.Clock()

    mediator = initialise_gui()

    player = Trackable(Player(), "player")
    mediator.add_trackable(player)
    time.sleep(1)

    paused = False
    running = True
    while running:
        while paused:
            screen.fill((0, 0, 0))
            clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_SPACE:
                        paused = False
            player.draw(screen)
            pygame.display.flip()

        screen.fill((0, 0, 0))
        clock.tick(60)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

        player.update()
        player.draw(screen)

        pygame.display.flip()

    pygame.quit()


if __name__ == "__main__":
    main()
