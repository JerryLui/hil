from multiprocessing import Process
from subprocess import *

import time
import random
import logging
import os


# -------------------- PROCESS --------------------
class Worker(Process):
    def __init__(self, file_path, task_id, log_path, lock, pipe):
        self.file_path = file_path
        self.task_id = task_id
        self.log_path = log_path
        self.lock = lock
        self.pipe = pipe
        super().__init__()

    def run(self):
        logger = logging.getLogger(self.log_path[-8:])  # arbitrary name
        handler = logging.FileHandler(self.log_path)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s ')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.info('Logging initialized on %s.' % self.file_path)

        logger.info('Starting run...')
        self.pipe.send(2)
        time.sleep(random.randint(3, 4))

        while not self.lock.acquire(timeout=20):
            logger.info('Acquiring lock...')
            self.pipe.send(1)

        logger.info('Running...')
        self.pipe.send(3)
        time.sleep(random.randint(5, 10))

        if random.randint(0, 5):
            logger.info('Run successful.')
            self.pipe.send(4)
        else:
            logger.error('Run failed.')
            self.pipe.send(5)

        try:
            self.lock.release()
        except ValueError:
            pass

        self.pipe.close()
        logger.info('Process finished.')
        return
