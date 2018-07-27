from multiprocessing import Process
from subprocess import *
import time
import random
import logging

# LEVEL?
# -------------------- PROCESS --------------------
class FakeProcess(Process):
    def __init__(self, file_path, task_id, lock, pipe):
        self.file_path = file_path
        self.task_id = task_id
        self.lock = lock
        self.pipe = pipe
        super().__init__()

    def run(self):
        self.pipe.send(2)
        time.sleep(random.randint(3, 4))

        while not self.lock.acquire(timeout=20):
            self.pipe.send(1)

        self.pipe.send(3)
        time.sleep(random.randint(5, 10))

        if random.randint(0, 5):
            self.pipe.send(4)
        else:
            self.pipe.send(5)

        try:
            self.lock.release()
        except ValueError:
            pass

        self.pipe.close()
        return
