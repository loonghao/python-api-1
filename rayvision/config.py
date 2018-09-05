# -*- coding: utf-8 -*-
"""
module author: Long Hao <hoolongvfx@gmail.com>
"""
# Import built-in modules
import os
import sys

# Import local modules
import vendor.yaml as yaml
from rayvision.logger import RayLogger
from rayvision.vendor.addict import Dict

LOGGER = RayLogger.configure(__name__)


def entity_data(function_name):
    def _deco(*args, **kwargs):
        lists = []
        return_value = function_name(*args, **kwargs)
        if isinstance(return_value, list):
            for r in return_value:
                if isinstance(r, dict):
                    lists.append(Dict(r))
            return lists
        elif isinstance(return_value, dict):
            return Dict(return_value)
        else:
            return return_value

    return _deco


class _RvOs(object):
    is_win = 0
    is_linux = 0
    is_mac = 0

    if sys.platform.startswith("win"):
        os_type = "win"
        is_win = 1
    elif sys.platform.startswith("linux"):
        os_type = "linux"
        is_linux = 1
    else:
        os_type = "mac"
        is_mac = 1


class FoxConfig(_RvOs):
    UPLOAD = "upload_files"
    DOWNLOAD = "download_files"

    def __init__(self):
        self.root = os.path.dirname(__file__)
        config_file = os.getenv("FOX_API_CONFIG_PATH")
        if config_file:
            self._config_file = config_file
        else:
            self._config_file = os.path.join(self.root, "config", "schema.yaml")
        LOGGER.info("load config file: %s" % self._config_file)
        with open(self._config_file, 'r') as f:
            self.data = yaml.load(f)

    def get_api_version(self):
        return self.get_config_var("api_version")

    def get_api_url(self, render_server):
        return self.get_config_var("render_server").format(server=render_server)

    @entity_data
    def get_config_var(self, session, value=None):
        if value:
            if self.data.get(session):
                return os.path.expandvars(self.data.get(session)[value])
        else:
            if self.data.get(session):
                return os.path.expandvars(self.data.get(session))

    def get_rayvision_app(self):
        if self.is_win:
            app_path = os.path.join(self.root,
                                    "vendor",
                                    "rayvision",
                                    "windows",
                                    "rayvision_transmitter.exe")
            return app_path.replace(os.altsep, os.sep)
        else:
            return os.path.join(self.root,
                                "vendor",
                                "rayvision",
                                "centos",
                                "rayvision_transmitter")
