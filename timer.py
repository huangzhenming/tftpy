import time
import logger
import logging

class Timer(object):
    def __init__(self, name=None):
        self.name = name
        self._logger = logger.getLogger("Timer")

    def __enter__(self):
        self.tstart = time.time()

    def __exit__(self, type, value, traceback):
        # if self.name:
        #     self._logger.info('[%s]' %self.name)
        self._logger.info('Timer %s Elapsed:%s' %(self.name, time.time()-self.tstart))