import json
import os

from kafka import KafkaProducer
from mitmdump import DumpMaster, Options
from mitmproxy.http import HTTPFlow

# sys.path.append(os.path.dirname(os.path.realpath(__file__)))
from utils.config import InitConfig


class AddHeader:
    def __init__(self):
        # 本地配置
        self.root_path = os.path.dirname(__file__)[0:-5]
        self.con = InitConfig().getConfig("kafka")

        # kafka
        self.producer = KafkaProducer(bootstrap_servers=self.con["server"],
                                      value_serializer=lambda m: json.dumps(m).encode())

    def response(self, flow: HTTPFlow):
        # print(flow.response.get_state())

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
        # print(http)
        self.producer.send(self.con["topic"][1:-1], json.dumps(http))


addons = [
    AddHeader()
]

if __name__ == '__main__':
    opts = Options(listen_host='0.0.0.0', listen_port=8888, scripts=__file__)
    m = DumpMaster(opts)
    m.run()
