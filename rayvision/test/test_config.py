# -*- coding: utf-8 -*-
# Copyright (C) 2015 Pixomondo - All Rights Reserved.
# Confidential and proprietary.
# Unauthorized usage of this file, via any medium is strictly prohibited.

""".. moduleauthor:: Long Hao <hao.long@pixomondo.com>
"""

import os
import unittest

from rayvision.config import FoxConfig


class TestConfig(unittest.TestCase):
    def setUp(self):
        os.environ["FOX_API_CONFIG_PATH"] = os.path.join(os.path.dirname(__file__), "schema.yaml")

        self.setttings = FoxConfig()

    def test_use_config_env(self):
        self.assertEqual(self.setttings._config_file, os.getenv("FOX_API_CONFIG_PATH"))

    def test_get_config_var(self):
        return_value = self.setttings.get_config_var("transports", "ip")
        self.assertEqual(return_value, "111.111.111.111")

    def test_get_config_var2(self):
        os.environ["FOX_SERVER"] = "CTCC"
        return_value = self.setttings.get_config_var("transports", "server")
        self.assertEqual(return_value, "CTCC")
