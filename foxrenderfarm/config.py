# -*- coding: utf-8 -*-
"""
module author: Long Hao <hoolongvfx@gmail.com>
"""
import logging
import os
import sys

import vendor.yaml as yaml

log = logging.getLogger("FoxConfig")


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
    def __init__(self):
        self.root = os.path.dirname(__file__)
        config_file = os.path.join(self.root, "config", "schema.yaml")
        log.info("load config file: %s" % config_file)
        with open(config_file, 'r') as f:
            self.data = yaml.load(f)

    def get_api_version(self):
        return self.data.get("api_version")

    def get_api_url(self, render_server):
        return self.data.get("render_server").format(server=render_server)

    def get_rayvision_app(self):
        if self.is_win:
            return os.path.join(self.root, "vendor", "rayvision", "windows", "rayvision_transmitter.exe")
        else:
            return os.path.join(self.root, "vendor", "rayvision", "centos", "rayvision_transmitter")


if __name__ == '__main__':
    fox_config = FoxConfig()
    print fox_config.get_api_version()
