import threading
import sys
import pygame
import time


class ReturnThread(threading.Thread):
    def __init__(self, group=None, target=None, name=None, args=(), kwargs={}, daemon=False):
        threading.Thread.__init__(self, group, target, name, args, kwargs, daemon=daemon)
        self.result = None

    def run(self):
        if self._target is not None:
            self.result = self._target(*self._args, **self._kwargs)

    def join(self, *args):
        threading.Thread.join(self, *args)
        if self.result:
            return self.result


def responsive_blocking(target, args=()):
    """Runs blocking but pygame responsive function and returns value"""
    thread = ReturnThread(target=target, args=args, daemon=True)
    thread.start()
    while thread.is_alive():
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
        time.sleep(1/60)
    return (thread.join())
