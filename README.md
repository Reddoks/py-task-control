## Task Control

Simple task manager module for python scripts using `threading` library and in-memory `tinyDB` database. Initially conceived as a task manager for API application.

### Features:

- Run managed tasks with status control
- Run tasks depend on other tasks
- Limitation task execution time

### How to use:

Script need `tinyDB` external module, you have to install it:

``` python
pip install tinydb
```

Script use `TaskControl` class to declare properties and methods. To start, you have to just create task manager instance:

```python
from task-control import TaskControl

taskman = TaskControl()
```

Now you can run example task:

``` python
from time import sleep  
from task_control import TaskControl  
  
# Test function  
def worker():  
   print("Worker started")  
   for i in range(0,10):  
      sleep(1)  
      print(i)  
   print("Worker finished")  
  
  
if __name__ == '__main__':  
    # Class instance  
 taskman = TaskControl()  
    # Run task  
 task = taskman.add(name="Test worker task", function=lambda f: worker())  
    print("Task started:", task)  
    print("Task info:", taskman.get_task(task))  
    sleep(12)
```

As output, you can see task id, task information and worker 'ticks':

``` shell
Task started: d33dd55273
Task info: [{'id': 'd33dd55273', 'timestamp': '07.01.2022 20:32:15', 'name': 'Test worker task', 'depend_on': None, 'status': 3, 'get_result': False, 'perf': 0, 'error': None, 'result': None, 'thread': None}]
Worker started
0
1
```

You can get info for all tasks with `get_all` method. Task list can be also managed by standard `tinydb` methods using `TaskControl.db` and `TaskControl.dbQuery` instances.
Cleanup for tasks in database can be done with `purge` method:

``` python
taskman.purge(days=X,hours=X,minutes=X)
```

All arguments is optional here. If no argument provided - all records will be purged.

### Task Status

When task created, it will have  `status` = *2 (Suspended)*. Normal execution status flow is:
*2 (Suspended)* -> *3 (Running)* -> *0 (Completed)*. In case of task function exception, execution will be interrupted and status will set to *1 (Error)*, exception details will be stored in "error" job property. Status descriptions defined in `status_code` list:

| Code | Description |
| ---- | ----------- |
| 0    | Completed   |
| 1    | Error       |
| 2    | Suspended   |
| 3    | Running     |
| 4    | Canceled    |

`get_status` and `get_status_str` methods will return current code or description for task:

``` python
status_code = taskman.get_status(task) # Will return "3" for example
status_decription = taskman.get_status_str(task) # Will return "Running"
```

### Arguments and result

Arguments can be passed to task function as usual:

``` python
task = taskman.add(name="Test worker task", function=lambda f: worker(arg1, arg2)) 
```

If you need execution result, you can use `get_result` argument:

``` python
task = taskman.add(name="Test worker task", function=lambda f: worker(arg1, arg2), get_result=True) 
```

Then function return value will stored in "result" task property and can be retrieved by `get_result` method:

``` python
result = taskman.get_result(task)
```

### Task timeout

By default, task timeout is not set. You can change it with `thread_timeout` property i.e. set default timeout for all tasks:

``` python
# Set default job run timeout to 60 seconds
taskman.thread_timeout = 60
```

Or, you can set timeout for specific task:

``` python
task = taskman.add(name="Test worker task", function=lambda f: worker(), thread_timeout=6)
```

### Task chain

Argument `depend_on` can help to run task when previous task completed:

``` python
next_task = taskman.add(name="Next task", function=lambda f: worker(), depend_on=task)
```

Task `next_task` will be suspended until `task` completed. If previous task finished with 1 (Error) status, next task will be canceled with status 4 (Canceled).

Suspended tasks check depended task status in cycle. You can manage this behavior by `suspend_refresh` property.