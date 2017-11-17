# -*- coding: utf-8 -*-
# Copyright (C) 2017 RayVision - All Rights Reserved.
# Confidential and proprietary.
# Unauthorized usage of this file, via any medium is strictly prohibited.

# Copyright (C) 2017 Pixomondo - All Rights Reserved.
# Confidential and proprietary.
# Unauthorized usage of this file, via any medium is strictly prohibited.

""".. moduleauthor:: Long Hao <hao.long@pixomondo.com>
"""
import Queue
import copy
import json
import logging
import os
import pprint
import ssl
import subprocess
import sys
import threading
import urllib2
from functools import wraps

from foxrenderfarm.config import FoxConfig
from foxrenderfarm.error import AuthenticationFault
from foxrenderfarm.error import RayVisionArgsError
from foxrenderfarm.error import RayVisionError
from foxrenderfarm.vendor.attrdict import AttrDict

__version__ = "1.0.1"
__version__ += ".pxo"  # PIXOMONDO: CHANGE

LOGGER = logging.getLogger('foxrenderfarm')


def sslwrap(func):
    @wraps(func)
    def bar(*args, **kw):
        kw['ssl_version'] = ssl.PROTOCOL_TLSv1
        return func(*args, **kw)

    return bar


ssl.wrap_socket = sslwrap(ssl.wrap_socket)


def entity_data(function_name):
    def _deco(*args, **kwargs):
        lists = []
        return_value = function_name(*args, **kwargs)
        if isinstance(return_value, list):
            for r in return_value:
                if isinstance(r, dict):
                    lists.append(AttrDict(r))
            return lists
        elif isinstance(return_value, dict):
            return AttrDict(return_value)
        else:
            return return_value

    return _deco


class API(object):
    def __init__(self, render_server, logging_level="DEBUG"):
        self.settings = FoxConfig()
        self.url = self.settings.get_api_url(render_server)
        LOGGER.setLevel(logging_level)

    @entity_data
    def _post(self, data, q):
        LOGGER.debug("URL:%s" % self.url)
        LOGGER.debug("Post data:%s" % data)
        if isinstance(data, dict):
            data = json.dumps(data)
        try:
            request = urllib2.Request(self.url)
            request.add_header('content-TYPE', 'application/json')
            response = urllib2.urlopen(request, data)
            request_data = response.read()
        except urllib2.HTTPError, err:
            if err.code == 401:
                raise RayVisionError("Error: HTTP Status Code 401. Authentication with the Web Service failed."
                                     " Please ensure that the authentication credentials are set, are correct,"
                                     " and that authentication mode is enabled.")
            else:
                request_data = err.read()

        try:
            all_data = json.loads(request_data)
            LOGGER.info(pprint.pformat(all_data))
            q.put(all_data)
            return all_data
        except:
            return {}

    @entity_data
    def post(self, data):
        q = Queue.Queue()
        threading.Thread(target=self._post, args=(data, q)).start()
        result = q.get()
        return result


class Fox(API):
    root = os.path.dirname(os.path.abspath(__file__))

    def __init__(self, render_server, account, access_key, language="en", debug="DEBUG"):
        super(Fox, self).__init__(render_server, debug)
        self.data = {"head": {"access_key": access_key,
                              "account": account,
                              "msg_locale": language,
                              "action": ""},
                     "body": {}}
        self.login()

    def login(self):
        user_info = self.get_users()
        if user_info:
            self._init_upload_download_config(user_info[0])
        else:
            raise AuthenticationFault("Login failed.")

    def _init_upload_download_config(self, info):
        self.app = self.settings.get_rayvision_app()
        self.account_id = info.id
        self.upload_id = info.upload_id
        self.download_id = info.download_id
        self.transports = info.transports

        if self.transports:
            self.engine_type = self.transports[0].engine
            self.server_name = self.transports[0].server
            self.server_ip = self.transports[0].ip
            self.server_port = self.transports[0].port

    def submit_task(self, **kwargs):
        data = copy.deepcopy(self.data)
        submit_info = AttrDict(kwargs)
        if "action" in submit_info:
            data["head"]["action"] = submit_info.action
        else:
            data["head"]["action"] = "create_task"

        for i in submit_info:
            data["body"][i] = submit_info[i]
        if "project_name" not in submit_info:
            raise RayVisionArgsError("Missing project_name args, please check.")
        if "input_scene_path" not in submit_info:
            raise RayVisionArgsError("Missing input_scene_path args, please check.")
        if "frames" not in submit_info:
            raise RayVisionArgsError("Missing frames, please check args.")

        data["body"]["input_scene_path"] = data["body"]["input_scene_path"].replace(":", "").replace("\\", "/")
        data["body"]["submit_account"] = data["head"]["account"]

        project = self.get_projects(submit_info.project_name)
        if not project:
            raise RayVisionError("Project %s doesn't exists." % submit_info.project_name)
        plugins = project[0].plugins
        for plugin_info in plugins:
            if plugin_info.is_default:
                data["body"]["cg_soft_name"] = plugin_info.cg_soft_name
                data["body"]["plugin_name"] = plugin_info.plugin_name
                result = self.post(data)
                LOGGER.info('job id: %s' % result.body.data[0].task_id)
                if result.head.result == '0':
                    return int(result.body.data[0].task_id)
                else:
                    pprint.pprint(result)
                    return -1

    def submit_maya(self, **kwargs):
        return self.submit_task(**kwargs)

    def submit_houdini(self, **kwargs):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "create_houdini_task"

        if kwargs:
            for i in kwargs:
                if i != "rop_info":
                    data["body"][i] = kwargs[i]
                else:
                    data["body"]["layer_list"] = kwargs["rop_info"]
                    for j in data["body"]["layer_list"]:
                        j["layerName"] = j["rop"]
                        j.pop("rop")

            if "project_name" not in kwargs:
                raise Exception("Missing project_name args, please check.")
            if "input_scene_path" not in kwargs:
                raise Exception("Missing input_scene_path args, please check.")
            if "rop_info" not in kwargs:
                raise Exception("Missing rop info, please check args.")

        data["body"]["input_scene_path"] = data["body"]["input_scene_path"].replace(":", "").replace("\\", "/")

        project = self.get_projects(kwargs["project_name"])
        if not project:
            raise Exception("Project <%s> doesn't exists." % (kwargs["project_name"]))

        plugins = project[0]["plugins"]
        no_plugin = True
        for i in plugins:
            if i:
                no_plugin = False
                break
        if no_plugin:
            raise Exception("Project <%s> doesn't have any plugin settings." % (kwargs["project_name"]))

        default_plugin = [i for i in plugins
                          if "is_default" in i if i["is_default"] == '1']

        if len(plugins) == 1:
            default_plugin = plugins

        if not default_plugin:
            raise Exception("Project <%s> doesn't have a default plugin settings." % (kwargs["project_name"]))

        data["body"]["cg_soft_name"] = default_plugin[0]["cg_soft_name"]
        if "plugin_name" in default_plugin[0]:
            data["body"]["plugin_name"] = default_plugin[0]["plugin_name"]

        result = self.post(data)
        if result["head"]["result"] == '0':
            return int(result["body"]["data"][0]["task_id"])
        else:
            pprint.pprint(result)
            return -1

    def submit_blender(self, **kwargs):
        return self.submit_task(action="create_blender_task", **kwargs)

    @entity_data
    def get_users(self, has_child_account=0):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "query_customer"

        if not has_child_account:
            data["body"]["login_name"] = data["head"]["account"]

        result = self.post(data)
        logging.info(result)
        if result and result["head"]["result"] == "0":
            return result["body"]["data"]
        else:
            return []

    @entity_data
    def get_projects(self, project_name=None):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "query_project"

        if project_name:
            data["body"]["project_name"] = project_name

        result = self.post(data)
        if result["head"]["result"] == "0":
            return result["body"]["data"]
        else:
            return []

    @entity_data
    def get_tasks(self, task_id=None, project_name=None, has_frames=0, task_filter=None):
        if task_filter is None:
            task_filter = {}
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "query_task"

        if project_name:
            data["body"]["project_name"] = project_name

        if task_id:
            data["body"]["task_id"] = str(task_id)

        if has_frames:
            data["body"]["is_jobs_included"] = "1"

        if task_filter:
            for i in task_filter:
                data["body"][i] = task_filter[i]

        result = self.post(data)
        if result["head"]["result"] == "0":
            return result["body"]["data"]
        else:
            return []

    def upload(self, local_path_list, server_path='/'):

        transmit_type = self.settings.UPLOAD
        result = {}
        if isinstance(local_path_list, list):
            for i in set(local_path_list):
                if os.path.exists(i):
                    local_path = i
                    cmd = "echo y | %s %s %s %s %s %s %s %s %s %s" % (self.app,
                                                                      self.engine_type,
                                                                      self.server_name,
                                                                      self.server_ip,
                                                                      self.server_port,
                                                                      self.upload_id,
                                                                      self.account_id,
                                                                      transmit_type,
                                                                      local_path,
                                                                      server_path)
                    LOGGER.debug(cmd)
                    sys.stdout.flush()
                    result[i] = self.subprocess_run(cmd)
                else:
                    result[i] = "upload fail"
        else:
            LOGGER.error("please use list []")
        return result

    def download(self, task_id, local_path):
        transmit_type = self.settings.DOWNLOAD
        task = self.get_tasks(task_id)
        if task:
            input_scene_path = task[0]["input_scene_path"]
            server_path = "%s_%s" % (task_id, os.path.splitext(os.path.basename(input_scene_path))[0].strip())
            cmd = "echo y | %s %s %s %s %s %s %s %s %s %s" % (self.app,
                                                              self.engine_type,
                                                              self.server_name,
                                                              self.server_ip,
                                                              self.server_port,
                                                              self.download_id,
                                                              self.account_id,
                                                              transmit_type,
                                                              local_path,
                                                              server_path)
            LOGGER.debug(cmd)
            sys.stdout.flush()
            return self.subprocess_run(cmd)
        else:
            return False

    def get_server_files(self):
        pass

    def delete_server_files(self):
        pass

    """ NO 7.2.3
        :param project_name: the name of the project you want to create
        :param kwargs:  can be used to pass more arguments, not necessary
                        including project_path, render_os, remark, sub_account
    """

    def create_project(self, project_name, cg_soft_name, plugin_name="",
                       render_os="", **kwargs):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "create_project"
        if not render_os:
            if self.settings.is_win:
                render_os = "Windows"
            else:
                render_os = "Linux"

        data["body"]["render_os"] = render_os

        if not project_name:
            raise RayVisionArgsError("Missing project_name, please check")
        data["body"]["project_name"] = project_name
        for key, value in kwargs.items():
            data["body"][key] = value

        result = self.post(data=data)
        if result["head"]["result"] == '0':
            project_id = int(result["body"]["project_id"])
            self.add_project_config(project_id, cg_soft_name, plugin_name,
                                    is_default=1)
            self._message_output("INFO", "Project ID: {0}".format(project_id))
            return project_id
        else:
            return -1

    @staticmethod
    def _message_output(msg_type=None, msg=None):
        LOGGER.info("[%s]: %s" % (msg_type, msg))

    def get_plugins_available(self, **kwargs):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "query_plugin"
        for key, value in kwargs.items():
            data["body"][key] = value

        result = self.post(data=data)
        if result["head"]["result"] == "0":
            self._save_list2file(result["body"], "plugins.txt")
            return True, result["body"]
        else:
            self._message_output("ERROR", result["head"]["error_message"])
            return False

    @staticmethod
    def _save_list2file(list_data, file_name, remark="\n"):
        basedir = os.path.abspath(os.path.dirname(__file__))
        save_path = os.path.join(basedir, file_name)
        with open(save_path, "a+") as f:
            if remark:
                f.write(remark)
            for line in list_data:
                f.write(str(line) + "\n")
        print "[INFO]:" + save_path + " has saved."

    def add_project_config(self, project_id, cg_soft_name, plugin_name=None,
                           is_default=0, **kwargs):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "operate_project"
        data["body"]["operate_type"] = 0

        data["body"]["project_id"] = int(project_id)
        data["body"]["cg_soft_name"] = cg_soft_name
        if plugin_name:
            data["body"]["plugin_name"] = plugin_name
        data["body"]["is_default"] = is_default
        for key, value in kwargs.items():
            data["body"][key] = value

        result = self.post(data=data)
        if result["head"]["result"] == "0":
            return True
        else:
            return False

    @staticmethod
    def subprocess_run(command):
        p = subprocess.Popen(command,
                             stdin=subprocess.PIPE,
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True)
        p.wait()
        return p.stdout.readlines()

    def delete_project_config(self, project_id, config_id=None, **kwargs):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "operate_project"
        data["body"]["operate_type"] = 2

        data["body"]["project_id"] = int(project_id)
        if config_id:
            data["body"]["config_id"] = int(config_id)
        for key, value in kwargs.items():
            data["body"][key] = value

        result = self.post(data=data)
        if result["head"]["result"] == "0":
            self._message_output("INFO", "configuration delete")
            return True
        else:
            self._message_output("ERROR", result["head"]["error_message"])
            return False

    def modify_project_config(self, project_id, config_id, cg_soft_name,
                              plugin_name=None, is_default=None, **kwargs):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "operate_project"
        data["body"]["operate_type"] = 1

        data["body"]["project_id"] = int(project_id)
        data["body"]["config_id"] = int(config_id)
        data["body"]["cg_soft_name"] = cg_soft_name
        if plugin_name is not None:
            data["body"]["plugin_name"] = plugin_name
        if is_default:
            data["body"]["is_default"] = int(is_default)
        for key, value in kwargs.items():
            data["body"][key] = value

        result = self.post(data=data)
        if result["head"]["result"] == "0":
            self._message_output("INFO", "modify the configuration")
            return True
        else:
            self._message_output("ERROR", result["head"]["error_message"])
            return False

    def restart_tasks(self, task_id, restart_type="0"):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "operate_task"
        data["body"]["operate_order"] = "1"
        data["body"]["restart_type"] = str(restart_type)
        if isinstance(task_id, list) and len(task_id) > 1:
            task_id = ''.join([str(id) + ',' for id in task_id[:-1]]) + str(task_id[-1])
        data["body"]["task_id"] = str(task_id)

        result = self.post(data=data)
        if result["head"]["result"] == "0":
            self._message_output("INFO", "task {0} restart.".format(task_id))
            return True
        else:
            self._message_output("ERROR", result["head"]["error_message"])
            return False

    def stop_tasks(self, task_id):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "operate_task"
        data["body"]["operate_order"] = "0"
        if isinstance(task_id, list) and len(task_id) > 1:
            task_id = ''.join(map(lambda id: str(id) + ",", task_id[:-1])) + str(task_id[-1])
        data["body"]["task_id"] = str(task_id)

        result = self.post(data=data)
        if result["head"]["result"] == "0":
            self._message_output("INFO", "task {0} paused.".format(task_id))
            return True
        else:
            self._message_output("ERROR", result["head"]["error_message"])
            return False

    def delete_tasks(self, task_id):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "operate_task"
        data["body"]["operate_order"] = "2"
        if isinstance(task_id, list) and len(task_id) > 1:
            task_id = ''.join(map(lambda id: str(id) + ",", task_id[:-1])) + str(task_id[-1])
        data["body"]["task_id"] = str(task_id)

        result = self.post(data=data)
        if result["head"]["result"] == "0":
            self._message_output("INFO", "task {0} deleted.".format(task_id))
            return True
        else:
            self._message_output("ERROR", result["head"]["error_message"])
            return False

    def get_project_plugins_config(self, project_name):
        data = copy.deepcopy(self.data)
        data["head"]["action"] = "query_project"

        if not project_name:
            self._message_output("WARNING", "Mising project name")
            return []

        data["body"]["project_name"] = project_name

        result = self.post(data)
        plugins = []
        if result["body"]["data"]:
            plugins = result["body"]["data"][0]["plugins"]

        if result["head"]["result"] == "0":
            self._message_output("INFO", "Query plugins config id:")
            return plugins
        else:
            self._message_output("WARNING", result["head"]["error_message"])
            return []
