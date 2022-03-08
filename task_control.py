# Small module for API tasks control
# Imports
import ctypes, threading
from datetime import datetime as dt, timedelta as td
from tinydb import TinyDB, Query, where
from tinydb.storages import MemoryStorage
from uuid import uuid4
from time import perf_counter, sleep
from threading import *
from queue import Queue


# Task Control class
class TaskControl:
    def __init__(self):
        # Define default timeout for task threads
        self.thread_timeout = None
        # Define suspended task refresh time in seconds
        self.suspend_refresh = 3
        # Database init
        self.db = TinyDB(storage=MemoryStorage)
        # Query init
        self.dbQuery = Query()
        # Codes list
        self.status_code = [
            "Completed",
            "Error",
            "Suspended",
            "Running",
            "Canceled"
        ]

    # Adding task to list. Dependency is optional
    def add(self, name, function, depend_on=None, get_result=False, thread_timeout=None, args=None):
        task_status = 2  # New task is suspended before run
        task_id = str(uuid4().hex)[:10]  # Task uid
        timestamp, timestamp_formatted = self.__get_timestamp()
        # Store task info in db
        self.db.insert(
            {"id": task_id, "timestamp": timestamp, "timestamp_formatted": timestamp_formatted, "name": name,
             "depend_on": depend_on,
             "status": task_status, "get_result": get_result, "perf": 0, "error": None, "result": None, "thread": None})
        # Create and run thread for task
        thread = Thread(target=self.__run, args=(task_id, function, thread_timeout, args))
        thread.start()
        return task_id

    # Run task thread
    def __run(self, task_id, function, thread_timeout=None, args=None):
        # Query DB for task info
        task_d = self.db.search(self.dbQuery.id == task_id)
        # Check task dependency
        if task_d[0]["depend_on"] != None:
            # Task has dependency
            while True:
                # Looking depended task
                dep_task = self.db.search(self.dbQuery.id == task_d[0]["depend_on"])
                # If it is in completed state - continue
                if dep_task[0]["status"] == 0:
                    break
                # If it in error or terminated state - terminate task
                if (dep_task[0]["status"] == 1) | (dep_task[0]["status"] == 4):
                    self.db.update({"status": 4}, self.dbQuery.id == task_id)
                    return
                sleep(self.suspend_refresh)
        # Update thread status to 'Running'
        self.db.update({"status": 3}, self.dbQuery.id == task_id)
        # Starting performance counter for task thread
        start_time = perf_counter()
        # Setting thread timeout
        thd_timeout = self.thread_timeout
        if thread_timeout:
            thd_timeout = thread_timeout
        # Starting thread and await it finish
        # Define queue for result
        que = Queue()

        # Exception hook for handle exceptions inside task thread
        def thread_exception(e):
            # Getting ident for crashed thread
            crashed_thread = e.thread.ident
            # Finding crashed task
            job = self.db.search(self.dbQuery.thread == crashed_thread)
            # Update task
            self.db.update({"status": 1, "error": str(e)}, self.dbQuery.thread == crashed_thread)
            return

        threading.excepthook = thread_exception
        try:
            print("Try to start:", task_d[0]["name"])
            # Form thread object
            task_thread = Thread(target=lambda q, arg1: q.put(function(arg1)), args=(que, args))
            # Starting thread
            task_thread.start()
            self.db.update({"thread": task_thread.ident}, self.dbQuery.id == task_id)
            # Wait until thread complete or timeout event
            task_thread.join(timeout=thd_timeout)
            # When time is over, check thread is alive
            if task_thread.is_alive():
                # If thread still running, kill thread and update database
                self.db.update({"status": 1, "error": "Killed by timeout"}, self.dbQuery.id == task_id)
                self.__terminate_thread(task_thread)
                return
            # Set task status in database
            if task_d[0]["get_result"]:
                return_value = que.get()
            else:
                return_value = None
            end_time = perf_counter()
            # Check completed task before final update
            finished_task = self.db.search(self.dbQuery.id == task_id)
            # If no error message there - update as completed
            if finished_task[0]["error"] is None:
                self.db.update({"status": 0, "perf": f'{end_time - start_time: 0.3f}', "result": return_value},
                               self.dbQuery.id == task_id)
            return
        except Exception as e:
            self.db.update({"status": 1, "error": str(e)}, self.dbQuery.id == task_id)
            self.__terminate_thread(task_thread)
            return

    # Get timestamp string
    def __get_timestamp(self):
        timestamp = dt.now()
        timestamp_formatted = timestamp.strftime('%d.%m.%Y %H:%M:%S')
        return timestamp, timestamp_formatted

    # Forced thread termination
    def __terminate_thread(self, thread):
        exc = ctypes.py_object(SystemExit)
        res = ctypes.pythonapi.PyThreadState_SetAsyncExc(
            ctypes.c_long(thread.ident), exc)
        if res == 0:
            raise ValueError("nonexistent thread id")
        elif res > 1:
            # """if it returns a number greater than one, you're in trouble,
            # and you should call it again with exc=NULL to revert the effect"""
            ctypes.pythonapi.PyThreadState_SetAsyncExc(thread.ident, None)
            raise SystemError("PyThreadState_SetAsyncExc failed")

    # Get all tasks
    def get_all(self):
        tasks = self.db.all()
        return tasks

    # Get task by ID
    def get_task(self, id):
        task = self.db.search(self.dbQuery.id == id)
        return task

    # Get task result by ID
    def get_result(self, id):
        task = self.db.search(self.dbQuery.id == id)
        result = task[0]['result']
        return result

    # Get task status by ID
    def get_status(self, id):
        task = self.db.search(self.dbQuery.id == id)
        status = task[0]['status']
        return status

    # Get task status string by ID
    def get_status_str(self, id):
        task = self.db.search(self.dbQuery.id == id)
        status = self.status_code[task[0]['status']]
        return status

    # Purge task records older than
    def purge(self, days=None, hours=None, minutes=None):
        older_than = dt.now()
        if days: older_than = older_than - td(days=days)
        if hours: older_than = older_than - td(hours=hours)
        if minutes: older_than = older_than - td(minutes=minutes)
        self.db.remove(self.dbQuery.timestamp < older_than)
        return