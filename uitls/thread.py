import ctypes
import inspect
import re
import threading


def _async_raise(tid, exctype):
    """raises the exception, performs cleanup if needed"""
    tid = ctypes.c_long(tid)

    if not inspect.isclass(exctype):
        exctype = type(exctype)
    res = ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, ctypes.py_object(exctype))
    if res == 0:
        raise ValueError("invalid thread id")

    elif res != 1:
        # """if it returns a number greater than one, you're in trouble,
        # and you should call it again with exc=NULL to revert the effect"""
        ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, None)
        raise SystemError("PyThreadState_SetAsyncExc failed")


def stop_thread(thread):
    _async_raise(thread.ident, SystemExit)


class GetLogThread(threading.Thread):
    def __init__(self, deviceItem, producer, stream_stop, t_name, config):
        threading.Thread.__init__(self)
        self.deviceItem = deviceItem
        self.producer = producer
        self.stream_stop = stream_stop
        self.name = t_name
        self.config = config

    def run(self):
        self.deviceItem.shell("logcat --clear")
        stream = self.deviceItem.shell("logcat | grep TRACK_SENSORS", stream=True)

        with stream:
            f = stream.conn.makefile()

            while True:
                line = f.readline()
                js_line = re.findall(r'\{.*\}', line.rstrip())[0]
                dt_line = eval(
                    js_line.replace("\"", "\'").replace("true", "True").replace("false", "False"))
                # print(self.config["topic"])
                dt_line["serialName"] = str(self.deviceItem)
                print(dt_line)
                if self.stream_stop():
                    pass
                else:
                    # topic
                    # print(self.config["topic"][1:-1])
                    self.producer.send("kafkatest", dt_line)