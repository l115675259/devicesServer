import configparser
import json
import os
import threading

from kafka import KafkaConsumer, KafkaProducer
from mitmdump import DumpMaster, Options
from mitmproxy import flowfilter, ctx, addonmanager
from mitmproxy.tcp import TCPFlow

from uitls.proxy import ProServer


class FilterFlow:
    def __init__(self, producer):
        self.filter = None
        self.producer = producer

        self.root_path = os.path.dirname(__file__)[0:-5]
        self.con = configparser.ConfigParser()
        self.con.read(self.root_path + "/config.ini", encoding='utf-8')
        self.config = dict(self.con.items("kafka"))

    def load(self, loader: addonmanager.Loader):
        self.filter = flowfilter.parse(ctx.options.dumper_filter)

    def response(self, flow):
        if flowfilter.match(self.filter, flow):
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
            if flow.request.url == "https://test1-api.520yidui.com/v3/video_room/recom_session":
                print(f"url: {flow.request.url}, query:{flow.request.query}")
                self.producer.send("kafkatest", json.dumps(f"url: {flow.request.url}, query:{flow.request.content}"))
            # self.producer.send("kafkatest", json.dumps(http))

    def tcp_message(self, flow: TCPFlow):
        if flowfilter.match(self.filter, flow):
            print(flow)


class ProxyServer:

    def __init__(self):
        # 本地配置
        self.root_path = os.path.dirname(__file__)[0:-5]
        self.con = configparser.ConfigParser()
        self.con.read(self.root_path + "/config.ini", encoding='utf-8')

        # kafka
        self.producer = KafkaProducer(bootstrap_servers=self.__config("kafka")["server"],
                                      value_serializer=lambda m: json.dumps(m).encode())
        # self.consumer = KafkaConsumer(self.__config("kafka")["topic"],
        #                               bootstrap_servers=self.__config("kafka")["server"],
        #                               group_id='test',
        #                               auto_offset_reset='earliest')

        # mitmproxy
        self.addons = [
            FilterFlow(self.producer)
        ]

    def __config(self, arg):
        return dict(self.con.items(arg))

    def run(self):
        opts = Options(listen_host=self.__config("mitmproxy")["server"],
                       listen_port=int(self.__config("mitmproxy")["port"]), scripts=None, dumper_filter='~m POST',
                       flow_detail=1, termlog_verbosity='info', show_clientconnect_log=False)
        m = DumpMaster(opts)
        m.addons.add(*self.addons)
        threading.Thread(target=m.run())
        threading.Thread(target=m.shutdown())


if __name__ == '__main__':
    ProxyServer().run()