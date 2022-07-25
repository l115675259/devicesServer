import os

from utils.config import InitConfig


class OsUtils:
    def __init__(self):
        self.con = InitConfig()

    def proxy(self, filterExp):
        if filterExp == "0":
            # root_path = os.path.dirname(__file__)[0:-5]
            # print(os.popen("cd /utils").read())
            os.popen(f"mitmdump -s proxyServer.py -p 8888")
            return "proxy: on"
        elif filterExp != "0":
            cmd = "mitmdump -s proxyServer.py -p 8888 " + str(filterExp)
            os.system(cmd)
            return "proxy: on"
        elif filterExp is None:
            return "请输入完整参数"

    def shutDownProxy(self):
        cmd = "lsof -i:8888 -t"
        text = os.popen(cmd).read().split("\n")[0]
        print(text)
        os.system("kill " + str(text))

        return "proxy killed"
