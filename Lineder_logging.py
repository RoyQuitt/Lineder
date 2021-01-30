# Logging for Lineder
import logging
import sys
from logging.handlers import TimedRotatingFileHandler

FORMATTER = logging.Formatter ("%(asctime)s—%(process)d-%(thread)d-%(name)s — %(levelname)s — %(message)s")
CONSOLE_FORMATTER = logging.Formatter ("%(asctime)s — %(message)s")
LOG_FILE = "Lineder.log"


def get_console_handler ():
    console_handler = logging.StreamHandler (sys.stdout)
    console_handler.setFormatter (CONSOLE_FORMATTER)
    return console_handler


def get_file_handler ():
    file_handler = TimedRotatingFileHandler (LOG_FILE, when='midnight')
    file_handler.setFormatter (FORMATTER)
    return file_handler


def get_logger (logger_name):
    """

   @rtype: object
   """
    logger = logging.getLogger (logger_name)
    logger.setLevel (logging.DEBUG)  # better to have too much log than not enough
    logger.addHandler (get_console_handler ())
    logger.addHandler (get_file_handler ())
    # with this pattern, it's rarely necessary to propagate the error up to parent
    logger.propagate = False
    return logger
