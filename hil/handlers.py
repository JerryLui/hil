from multiprocessing import Process
from subprocess import *

import time
import random
import logging
import os


# -------------------- PROCESS --------------------
class Worker(Process):
    def __init__(self, file_path, software_path, task_id, log_path, lock, pipe):
        self.file_paths = file_path if type(file_path) is list else [file_path]
        self.software_path = software_path
        self.task_id = task_id
        self.log_path = log_path
        self.lock = lock
        self.pipe = pipe
        super().__init__()

    def run(self):
        # Initiate logger
        logger = logging.getLogger(self.log_path[-8:])  # arbitrary name
        handler = logging.FileHandler(self.log_path)
        formatter = logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s ')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)
        logger.info('Logging initialized on:\n' + '\n\t'.join(self.file_paths))

        # Prepare for run
        logger.info('Running software: ' + self.software_path)
        self.pipe.send(2)
        time.sleep(random.randint(3, 4))

        # Acquire a lock
        while not self.lock.acquire(timeout=20):
            logger.info('Acquiring lock...')
            self.pipe.send(1)

        # Run software on logs
        for file in self.file_paths:
            logger.info('Starting run on: %s.' % file)
            self.pipe.send(3)
            time.sleep(random.randint(5, 10))

        # Validate log
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
