'''
Logging for Lineder
'''

import logging
import sys
from logging.handlers import TimedRotatingFileHandler
FORMATTER = logging.Formatter("%(process)d-%(thread)d-%(asctime)s—(name)s— %(message)s")
CONSOLE_FORMATTER = logging.Formatter("%(asctime)s — %(message)s")
LOG_FILE = "./logs/Lineder.log"


def get_console_handler():
      """
      a getter for the console handler
      :return: The console handler
      """
      console_handler = logging.StreamHandler(sys.stdout)
      console_handler.setFormatter(CONSOLE_FORMATTER)
      return console_handler


def get_file_handler():
      """
      Creates the file handler and returns it
      :return: the file handler
      """
      file_handler = TimedRotatingFileHandler(LOG_FILE, when='midnight')
      file_handler.setFormatter(FORMATTER)
      return file_handler


def get_logger(logger_name):
      """
      Create the logger
      :param logger_name:a string to use as the logger name
      :return: The logger object
      """
      logger = logging.getLogger(logger_name)
      logger.setLevel(logging.DEBUG) # better to have too much log than not enough
      logger.addHandler(get_console_handler())
      logger.addHandler(get_file_handler())
      # with this pattern, it's rarely necessary to propagate the error up to parent
      logger.propagate = False
      return logger
