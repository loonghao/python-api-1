# Fox Render Farm / Renderbus cloud rendering Python API
We provide a simple Python-based API for using our cloud rendering service. This is the official API that is maintained by Fox Render Farm / Renderbus R&D team

## Supporting Software
- Maya

## Submitting Maya Task Step
- You must have a Fox Render Farm / Renderbus account to use our service, then create a project and select the plugins you want to use on our web site before Submitting.

- Login in our cloud server account first, some information such as access key, you need ask for our support team.
```py
from foxrenderfarm import Fox
fox = Fox(render_server="www5.renderbus.com", account="XXX", access_key="XXX")
```

- Upload local files or folders to cloud server and skip the existing same file by default.
```py
fox.upload(local_path_list=[r"v:\project\shot\lgt.ma", r"v:\project\asset\sourceimages"])
```

- Create the project
```py
fox.create_project(project_name="XXX", cg_soft_name="maya 2015", plugin_name="pgYetiMaya 1.3.17")
```

- After all the dependancy files of Maya Task such as texture, cache etc have been uploaded, you can submit task to cloud server.
```py
fox.submit_task(project_name="XXX", input_scene_path=r"v:\project\shot\lgt.ma", frames="1-10[1]")
```

- You can also try below method to add some extra info to submit the task.
```py
task_info = {"project_name": "api",
               "input_scene_path": r"E:\test_files\2014_api_camera_layer.mb",
               "frames": "1073-1073[1]",
               "render_layer": "ball",
               "camera": "camera1"}
fox.submit_task(**task_info)
```

- After rendering complete, you can download the entire task output files from cloud server, but single frame download function is not supported yet. The download method will skip the existing same files which already downloaded by default.
```py
fox.download(task_id=11111, local_path=r"v:\project\output")
```

## Submitting Houdini Task Step
- Submitting houdini task step is very similar with maya task, the main difference is using `fox.submit_houdini()` method instead of the `fox.submit_task()` method.
- Create the project
```py
fox.create_project(project_name="XXX", cg_soft_name="houdini 13")
```
- Cause houdini need some specific args to set the rop node info, so the task_info dict must be created firstly, please look at below code.
- option `-1` means render process and `0` means simulation process.
```py
task_info = {"project_name": "XXX",
               "input_scene_path": r"D:\renderFile\test.hip",
               "rop_info":  [{"frames": "1-240[1]",
                              "rop": "/obj/grid_object1/rop_geometry1",
                              "option": "0"},
                             {"frames": "1-20[1]",
                              "rop": "/out/mantra1",
                              "option": "-1"}]
             }             
fox.submit_houdini(**task_info)
```

## Submitting Blender Task Step
- Submitting blender task step is very similar with maya task, the main difference is using `fox.submit_blender()` method instead of the `fox.submit_task()` method.
- Create the project
```py
fox.create_project(project_name="XXX", cg_soft_name="blender 2.78c")
```
- Submit blender task
```py
fox.submit_blender(project_name="XXX", input_scene_path=r"D:\renderFile\blender276_test\test_276.blend", frames="1-10[1]")
```

## Query Method
 - get user info
```py
fox.get_users()
```

- get all projects
```py
fox.get_projects()
```

- get specific project info
```py
fox.get_projects(project_name="XXX")
```

- get all tasks
```py
fox.get_tasks()
```

- get task using task filter
```py
task_filter={"project_name": "XXX", "task_status": "Start"}
task_filter={"project_name": "XXX", "task_status": "System_Done"}
fox.get_tasks(task_filter=task_filter)
```

- get all tasks of specific project
```py
fox.get_tasks(project_name="XXX")
```

- get specific task
```py
fox.get_tasks(task_id=11111)
```

- get specific task with frames info
```py
fox.get_tasks(task_id=11111, has_frames=1)
```

## Some operation of task

- submit_task()
- get_tasks()

- stop the task

```py
fox.stop_tasks(task_id=23456)
```

- delete the task

```py
fox.delete_tasks(task_id=12345)
```

- restart the task

```py
fox.restart_tasks(task_id=12345, restart_type=1)
```

restart_type:  

0 -- restart the failed frames

1 -- restart the frames that give up

2 -- restart the finished frames

3 -- restart the start frames

4 -- restart the waiting frames
