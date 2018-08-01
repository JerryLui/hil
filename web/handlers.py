from multiprocessing import Process
from subprocess import *
import time
import random
import logging
import os


# -------------------- PROCESS --------------------
class FakeProcess(Process):
    def __init__(self, file_path, task_id, lock, pipe):
        self.file_path = file_path
        self.task_id = task_id
        self.lock = lock
        self.pipe = pipe

        self.log_name = ''.join([os.path.splitext(self.file_path)[0], '_', str(task_id), '.log'])
        # logger = logging.getLogger(os.path.split(self.log_name)[1])
        handler = logging.FileHandler(self.log_name)
        # logging.Formatter('[%(asctime)s] %(levelname)s: %(message)s ')
        # self.logger.addHandler(self.handler)
        # self.logger.setLevel(logging.DEBUG)
        # logger.setLevel(logging.DEBUG)
        # logger.addHandler(handler)
        # logger.info('TEST1')

        # logging.info('Initiated process on: ', self.file_path)
        # logging.info('Task ID: ', str(self.task_id))
        super().__init__()

    def run(self):
        # logging.info('Starting run...')
        self.pipe.send(2)
        time.sleep(random.randint(3, 4))

        while not self.lock.acquire(timeout=20):
            # self.logger.info('Acquiring lock...')
            self.pipe.send(1)

        # self.logger.info('Running...')
        self.pipe.send(3)
        time.sleep(random.randint(5, 10))

        if random.randint(0, 5):
            # self.logger.info('Run successful.')
            self.pipe.send(4)
        else:
            # self.logger.error('Run failed.')
            self.pipe.send(5)

        try:
            self.lock.release()
        except ValueError:
            pass

        self.pipe.close()
        # self.logger.info('Process finished.')
        return
