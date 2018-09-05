# -*- coding: utf-8 -*-
# Copyright (C) 2017 RayVision - All Rights Reserved.
# Confidential and proprietary.
# Unauthorized usage of this file, via any medium is strictly prohibited.
"""
module author: Long Hao <hoolongvfx@gmail.com>
"""

# Import built-in modules
import copy
import json
import logging
import os
import pprint
import re
import subprocess
import sys
import urllib2

# Import local modules
from rayvision.config import Dict, FoxConfig, entity_data
from rayvision.config import RayLogger
from rayvision.error import AuthenticationFault
from rayvision.error import ERROR_FEEDBACK
from rayvision.error import RayVisionArgsError
from rayvision.error import RayVisionError

LOGGER = RayLogger.configure(__name__)


class RayVisionAPI(object):

    def __init__(self, render_server, logging_level="INFO"):
        self.settings = FoxConfig()
        self.render_server = render_server
        self.url = self.settings.get_api_url(render_server)
        LOGGER.setLevel(logging_level.upper())

    @entity_data
    def _post(self, data):
        LOGGER.debug("URL:%s", self.url)
        LOGGER.debug("Post data:%s", data)
        if isinstance(data, dict) or isinstance(data, Dict):
            data = json.dumps(data)
        try:
            request = urllib2.Request(self.url)
            request.add_header('content-TYPE', 'application/json')
            response = urllib2.urlopen(request, data)
            request_data = response.read()
        except urllib2.HTTPError, err:
            if err.code == 401 or err.code == 403:
                raise RayVisionError(
                    "Error: HTTP Status Code 401."
                    " Authentication with the Web Service failed."
                    " Please ensure that the authentication credentials are set,"
                    " are correct,"
                    " and that authentication mode is enabled.")
            else:
                request_data = err.read()
        all_data = json.loads(request_data)
        LOGGER.debug(pprint.pformat(all_data))
        return all_data

    @entity_data
    def post(self, data):
        return self._post(data)


class RayVision(RayVisionAPI):
    root = os.path.dirname(os.path.abspath(__file__))

    def __init__(self,
                 render_server,
                 account,
                 access_key,
                 language="en",
                 logging_level="INFO"):
        super(RayVision, self).__init__(render_server, logging_level)
        self.data = Dict({
            "head": {
                "access_key": access_key,
                "account": account,
                "msg_locale": language,
                "action": ""
            },
            "body": {
                "amount": 100
            }
        })
        self.login()

    def __repr__(self):
        return '<%s "%s">' % (self.__class__.__name__, self.render_server)

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
        self.transports = self.settings.get_config_var("transports")
        if self.transports:
            self.engine_type = self.transports.engine
            self.server_name = self.transports.server
            self.server_ip = self.transports.ip
            self.server_port = self.transports.port
        else:
            self.transports = info.transports

            if self.transports:
                self.engine_type = self.transports[0].engine
                self.server_name = self.transports[0].server
                self.server_ip = self.transports[0].ip
                self.server_port = self.transports[0].port

    def submit_task(self, **kwargs):
        data = self.data.deepcopy()
        submit_info = Dict(kwargs)
        if "action" in submit_info:
            data.head.action = submit_info.action
        else:
            data.head.action = "create_task"
        for i in submit_info:
            data.body[i] = submit_info[i]
        if "project_name" not in submit_info:
            raise RayVisionArgsError("Missing project_name args, please check.")
        if "input_scene_path" not in submit_info:
            raise RayVisionArgsError(
                "Missing input_scene_path args, please check.")
        if "frames" not in submit_info:
            raise RayVisionArgsError("Missing frames, please check args.")
        input_scene_path = data.body.input_scene_path.replace("\\", "/")
        drive, path_ = os.path.splitdrive(input_scene_path)
        data.body.input_scene_path = "%s%s" % (drive.upper(), path_)
        data.body.submit_account = data.head.account
        project = self.get_projects(submit_info.project_name)
        if not project:
            raise RayVisionError(
                "Project {} doesn't exists.".format(submit_info.project_name))
        plugins = project[0].plugins
        for plugin_info in plugins:
            if plugin_info.is_default == "0":
                data.body.cg_soft_name = plugin_info.cg_soft_name
                data.body.plugin_name = plugin_info.plugin_name
                result = self.post(data)
                if result.head.result == '0':
                    pprint.pprint(result)
                    LOGGER.info('job id: %s' % result.body.data[0].task_id)
                    return int(result.body.data[0].task_id)
                else:
                    LOGGER.debug(pprint.pformat(result))
                    raise RayVisionError(result.head.error_message)

    def submit_maya(self, **kwargs):
        return self.submit_task(**kwargs)

    def submit_houdini(self, kwargs):
        data = self.data.deepcopy()
        submit_info = Dict(kwargs)
        data.head.action = "create_houdini_task"
        if submit_info:
            for i in submit_info:
                if i != "rop_info":
                    data.body[i] = submit_info[i]
                else:
                    data.body.layer_list = submit_info.rop_info
                    for j in data.body.layer_list:
                        j.layerName = j.rop
                        j.pop("rop")
            if "project_name" not in submit_info:
                raise RayVisionError("Missing project_name args, please check.")
            if "input_scene_path" not in submit_info:
                raise RayVisionError(
                    "Missing input_scene_path args, please check.")
            if "rop_info" not in submit_info:
                raise RayVisionError("Missing rop info, please check args.")

        data.body.input_scene_path = data.body.input_scene_path.replace(
            ":", "").replace("\\", "/")

        project = self.get_projects(submit_info.project_name)
        if not project:
            raise RayVisionError(
                "Project <{}> doesn't exists.".format(
                    submit_info.project_name))

        plugins = project[0].plugins
        for i in plugins:
            if i:
                raise RayVisionError(
                    "Project <{}> doesn't have any plugin settings.".format(
                        submit_info.project_name))

        default_plugin = [
            i for i in plugins if "is_default" in i if i.is_default == '1'
        ]

        if len(plugins) == 1:
            default_plugin = plugins

        if not default_plugin:
            raise RayVisionError(
                "Project <{}> doesn't have a default plugin settings.".format(
                    submit_info.project_name))

        data.body.cg_soft_name = default_plugin[0].cg_soft_name
        if "plugin_name" in default_plugin[0]:
            data.body.plugin_name = default_plugin[0].plugin_name

        result = self.post(data)
        if result.head.result == '0':
            return int(result.body.data[0].task_id)
        else:
            pprint.pprint(result)
            return -1

    def submit_blender(self, **kwargs):
        return self.submit_task(action="create_blender_task", **kwargs)

    @entity_data
    def get_users(self, has_child_account=0):
        data = self.data.deepcopy()
        data.head.action = "query_customer"

        if not has_child_account:
            data.body.login_name = data.head.account

        result = self.post(data)
        logging.info(pprint.pformat(result))
        if result and result.head.result == "0":
            return result.body.data
        else:
            return []

    def get_projects(self, project_name=None):
        data = self.data.deepcopy()
        data.head.action = "query_project"
        if project_name:
            data.body.project_name = project_name
        result = self.post(data)
        if result.head.result == "0":
            return result.body.data
        else:
            return []

    @entity_data
    def get_tasks(self,
                  task_id=None,
                  project_name=None,
                  has_frames=False,
                  task_filter=None):
        if task_filter is None:
            task_filter = {}
        data = self.data.deepcopy()

        data.head.action = "query_task"

        if project_name:
            data.body.project_name = project_name

        if task_id:
            data.body.task_id = str(task_id)

        if has_frames:
            data.body.is_jobs_included = "1"

        if task_filter:
            for i in task_filter:
                data.body[i] = task_filter[i]
        result = self.post(data)
        if result.head.result == "0":
            return result.body.data
        else:
            return []

    def upload(self,
               local_file_path,
               remote_path='/',
               failure_count=1,
               keep_path="true"):
        transmit_type = self.settings.UPLOAD
        if os.path.exists(local_file_path):
            local_path = local_file_path
            LOGGER.info("start upload:%s", local_path)
            command = "{self.app} {self.engine_type}" \
                      " {self.server_name} {self.server_ip}" \
                      " {self.server_port} {self.upload_id}" \
                      " {self.account_id} {transmit_type}" \
                      " {local_path} {server_path}" \
                      " {failure_count} {keep_path}".format(self=self,
                                                            transmit_type=transmit_type,
                                                            local_path=local_path,
                                                            server_path=remote_path,
                                                            failure_count=failure_count,
                                                            keep_path=keep_path)
            LOGGER.debug(command)
            self.subprocess_run(command)
            return True
        raise RayVisionError(
            "Unanticipated error occurred uploading, \n"
            "Maybe this file does not exist: %s", local_file_path)

    def upload_files(self,
                     local_path_list,
                     remote_path='/',
                     failure_count=1,
                     keep_path="true"):
        transmit_type = self.settings.UPLOAD
        result = {}
        if isinstance(local_path_list, list):
            for i in set(local_path_list):
                if os.path.exists(i):
                    local_path = i
                    command = "{self.app} {self.engine_type}" \
                              " {self.server_name} {self.server_ip}" \
                              " {self.server_port} {self.upload_id}" \
                              " {self.account_id} {transmit_type}" \
                              " {local_path} {server_path}" \
                              " {failure_count} {keep_path}".format(self=self,
                                                                    transmit_type=transmit_type,
                                                                    local_path=local_path,
                                                                    server_path=remote_path,
                                                                    failure_count=failure_count,
                                                                    keep_path=keep_path)
                    LOGGER.debug(command)
                    sys.stdout.flush()
                    self.subprocess_run(command)
                    result[i] = True
                else:
                    result[i] = "upload fail"
        else:
            LOGGER.error("please use list []")
        LOGGER.debug(pprint.pprint(result))
        return result

    def download(self,
                 task_id,
                 local_path,
                 remote_path=None,
                 failure_count=1,
                 keep_path="false"):
        transmit_type = self.settings.DOWNLOAD
        task = self.get_tasks(task_id)
        if task:
            output_label = task[0].output_label
            if not remote_path:
                remote_path = "%s%s" % (task_id, output_label.strip())
            command = "{self.app} {self.engine_type}" \
                      " {self.server_name} {self.server_ip}" \
                      " {self.server_port} {self.download_id}" \
                      " {self.account_id} {transmit_type}" \
                      " {local_path} {server_path}" \
                      " {failure_count} {keep_path}".format(self=self,
                                                            transmit_type=transmit_type,
                                                            local_path=local_path,
                                                            server_path=remote_path,
                                                            failure_count=failure_count,
                                                            keep_path=keep_path)
            LOGGER.debug(command)
            self.subprocess_run(command)
            return True
        raise RayVisionError(
            "Unanticipated error occurred download: {}".format(task_id))

    def get_server_files(self):
        pass

    def delete_server_files(self):
        pass

    def create_project(self,
                       project_name,
                       cg_soft_name,
                       plugin_name="",
                       render_os="",
                       **kwargs):
        data = self.data.deepcopy()
        data.head.action = "create_project"
        if not render_os:
            if self.settings.is_win:
                render_os = "Windows"
            else:
                render_os = "Linux"

        data.body.render_os = render_os

        if not project_name:
            raise RayVisionArgsError("Missing project_name, please check")
        data.body.project_name = project_name
        for key, value in kwargs.items():
            data.body[key] = value

        result = self.post(data=data)
        if result.head.result == '0':
            project_id = int(result.body.project_id)
            self.add_project_config(
                project_id, cg_soft_name, plugin_name, is_default=1)
            LOGGER.info("Project ID: %s", project_id)
            return project_id
        else:
            raise RayVisionError("Create project failure")

    def get_plugins_available(self, **kwargs):
        data = self.data.deepcopy()
        data.head.action = "query_plugin"
        for key, value in kwargs.items():
            data.body[key] = value

        result = self.post(data=data)
        if result.head.result == "0":
            self._save_list2file(result.body, "plugins.txt")
            return result.body
        else:
            raise RayVisionError(result.head.error_message)

    @staticmethod
    def _save_list2file(list_data, file_name, remark="\n"):
        basedir = os.path.abspath(os.path.dirname(__file__))
        save_path = os.path.join(basedir, file_name)
        with open(save_path, "a+") as f:
            if remark:
                f.write(remark)
            for line in list_data:
                f.write(str(line) + "\n")
        LOGGER.info("%s has saved.", save_path)

    def add_project_config(self,
                           project_id,
                           cg_soft_name,
                           plugin_name=None,
                           is_default=0,
                           **kwargs):
        data = self.data.deepcopy()
        data.head.action = "operate_project"
        data.body.operate_type = 0

        data.body.project_id = int(project_id)
        data.body.cg_soft_name = cg_soft_name
        if plugin_name:
            data.body.plugin_name = plugin_name
        data.body.is_default = is_default
        for key, value in kwargs.items():
            data.body[key] = value

        result = self.post(data=data)
        if result.head.result == "0":
            return True
        else:
            return False

    @staticmethod
    def subprocess_run(command):
        p = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True)
        while p.poll() is None:
            line = p.stdout.readline()
            line = line.strip()
            if line:
                for feed_back in ERROR_FEEDBACK.keys():
                    match = re.match(feed_back, line)
                    if match:
                        raise RayVisionError(ERROR_FEEDBACK[feed_back])
                LOGGER.info('RayVision subprogram output: [%s]', line)
        p.wait()
        return p

    def delete_project_config(self, project_id, config_id=None, **kwargs):
        data = self.data.deepcopy()
        data.head.action = "operate_project"
        data.body.operate_type = 2

        data.body.project_id = int(project_id)
        if config_id:
            data.body.config_id = int(config_id)
        for key, value in kwargs.items():
            data.body[key] = value

        result = self.post(data=data)
        if result.head.result == "0":
            LOGGER.info("configuration delete")
            return True
        else:
            raise RayVisionError(result.head.error_message)

    def modify_project_config(self,
                              project_id,
                              config_id,
                              cg_soft_name,
                              plugin_name=None,
                              is_default=None,
                              **kwargs):
        data = self.data.deepcopy()
        data.head.action = "operate_project"
        data.body.operate_type = 1

        data.body.project_id = int(project_id)
        data.body.config_id = int(config_id)
        data.body.cg_soft_name = cg_soft_name
        if plugin_name is not None:
            data.body.plugin_name = plugin_name
        if is_default:
            data.body.is_default = int(is_default)
        for key, value in kwargs.items():
            data.body[key] = value

        result = self.post(data=data)
        if result.head.result == "0":
            LOGGER.info("modify the configuration")
            return True
        else:
            raise RayVisionError(result.head.error_message)

    def restart_tasks(self, task_id, restart_type="0"):
        data = copy.deepcopy(self.data)
        data.head.action = "operate_task"
        data.body.operate_order = "1"
        data.body.restart_type = str(restart_type)
        if isinstance(task_id, list) and len(task_id) > 1:
            task_id = ''.join([str(id_) + ',' for id_ in task_id[:-1]]) + str(
                task_id[-1])
        data.body.task_id = str(task_id)

        result = self.post(data=data)
        if result.head.result == "0":
            LOGGER.info("task %s restart.", task_id)
            return True
        else:
            raise RayVisionError(result.head.error_message)

    def stop_tasks(self, task_id):
        data = copy.deepcopy(self.data)
        data.head.action = "operate_task"
        data.body.operate_order = "0"
        if isinstance(task_id, list) and len(task_id) > 1:
            task_id = ''.join(map(lambda id: str(id) + ",",
                                  task_id[:-1])) + str(task_id[-1])
        data.body.task_id = str(task_id)

        result = self.post(data=data)
        if result.head.result == "0":
            LOGGER.info("task %s paused.", task_id)
            return True
        else:
            raise RayVisionError(result.head.error_message)

    def delete_tasks(self, task_id):
        data = copy.deepcopy(self.data)
        data.head.action = "operate_task"
        data.body.operate_order = "2"
        if isinstance(task_id, list) and len(task_id) > 1:
            task_id = ''.join(map(lambda id: str(id) + ",",
                                  task_id[:-1])) + str(task_id[-1])
        data.body.task_id = str(task_id)

        result = self.post(data=data)
        if result.head.result == "0":
            LOGGER.info("task %s deleted.", task_id)
            return True
        else:
            raise RayVisionError(result.head.error_message)

    def get_project_plugins_config(self, project_name):
        plugins = []
        data = self.data.deepcopy()
        data.head.action = "query_project"

        if not project_name:
            LOGGER.warning("Missing project name")
            return plugins

        data.body.project_name = project_name

        result = self.post(data)
        if result.body.data:
            plugins = result.body.data[0].plugins

        if result.head.result == "0":
            LOGGER.info("Query plugins config id:")
            return plugins
        else:
            LOGGER.warning(result.head.error_message)
            return plugins
