import configparser
import json
import os

from kafka import KafkaProducer


class InitConfig:

    def __init__(self):
        self.root_path = os.path.dirname(__file__)[0:-5]

        self.con = configparser.ConfigParser()
        self.con.read(self.root_path + "/config.ini", encoding='utf-8')
        self.config = dict(self.con.items('adbUtils'))

    def __config(self, arg):
        return dict(self.con.items(arg))

    def getConfig(self, arg):
        return self.__config(arg)

    def getKafka(self):
        producer = KafkaProducer(bootstrap_servers=self.__config("kafka")["server"],
                                 value_serializer=lambda m: json.dumps(m).encode())

        return producer
