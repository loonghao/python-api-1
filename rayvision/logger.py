# -*- coding: utf-8 -*-
"""
module author: Long Hao <hoolongvfx@gmail.com>
"""

# Import built-in modules
import logging

class RayLogger(object):
    @staticmethod
    def configure(name, level="info", path=None):
        level_dict = {'debug': logging.DEBUG,
                      'warning': logging.WARNING,
                      'critical': logging.CRITICAL,
                      'error': logging.ERROR,
                      'info': logging.INFO}
        full_name = "rayvision.%s" % name
        logging.basicConfig(
            format='{0}: %(asctime)-15s -- %(funcName)s "%(pathname)s:%(lineno)s" %(name)s\n%(message)s\n'.format(full_name),
            level=level_dict[level],
        )
        logger = logging.getLogger(full_name)
        for handler in logger.handlers:
            if hasattr(handler, "name") and handler.name == full_name:
                return logger

        if path:
            hdlr = logging.FileHandler(path)
        else:
            hdlr = logging.StreamHandler()
        hdlr.name = full_name
        logger.addHandler(hdlr)
        return logger
