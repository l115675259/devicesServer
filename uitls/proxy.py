import configparser
import json
import os

from kafka import KafkaProducer
from mitmproxy import flowfilter, addonmanager, ctx
from mitmproxy.http import HTTPFlow
from mitmproxy.options import Options
from mitmproxy.proxy.config import ProxyConfig
from mitmproxy.proxy.server import ProxyServer
from mitmproxy.tools.dump import DumpMaster

import threading
import asyncio
import time


class Addon(object):
    def __init__(self):
        self.num = 1
        self.producer = KafkaProducer(bootstrap_servers="192.168.108.212:9092",
                                      value_serializer=lambda v: json.dumps(v).encode('utf-8'))

    # def load(self, loader: addonmanager.Loader):
    #     self.filter = flowfilter.parse(ctx.options.dumper_filter)

    def request(self, flow):
        # flow.request.headers["count"] = str(self.num)
        pass

    def response(self, flow):
        def notNone(arg):
            if arg is None:
                return "None"
            else:
                return arg

        request = {
            "url": str(notNone(flow.request.url)),
            "host": str(flow.request.host),
            "timestamp_start": str(flow.request.timestamp_start),
            "path": str(flow.request.path),
            "query": str(flow.request.query),
            "headers": str(notNone(flow.request.headers)),
            "method": str(notNone(flow.request.method))
        }
        response = {
            "headers": str(notNone(flow.response.headers)),
            "content": str(notNone(flow.response.content))
        }
        http = {
            "request": request,
            "response": response
        }
        # if "https://test1-api.520yidui.com/v3/video_room/recom_session" in flow.request.url:
        #     self.producer.send("kafkatest", json.dumps(http))
        # print(http)
        self.producer.send("kafkatest", json.dumps(http))


# see source mitmproxy/master.py for details
def loop_in_thread(loop, m):
    asyncio.set_event_loop(loop)  # This is the key.
    m.run_loop(loop.run_forever)
    # asyncio.new_event_loop().run_until_complete(m)


class ProServer:

    def __init__(self):
        # 本地配置
        self.root_path = os.path.dirname(__file__)[0:-5]
        self.con = configparser.ConfigParser()
        self.con.read(self.root_path + "/config.ini", encoding='utf-8')

        # kafka
        self.producer = KafkaProducer(bootstrap_servers=self.__config("kafka")["server"],
                                      value_serializer=lambda m: json.dumps(m).encode())

        #  mitmdump
        self.options = Options(listen_host='0.0.0.0', listen_port=8888, http2=True)
        self.m = DumpMaster(self.options, with_termlog=False, with_dumper=False)
        self.config = ProxyConfig(self.options)
        self.m.server = ProxyServer(self.config)
        self.m.addons.add(Addon())

        # run mitmproxy in background, especially integrated with other server
        self.loop = asyncio.get_event_loop()

    def __config(self, arg):
        return dict(self.con.items(arg))

    def run(self):
        threading.Thread(target=loop_in_thread, args=(self.loop, self.m)).start()

    def shutdown(self):
        threading.Thread(target=self.m.shutdown()).start()

