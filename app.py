from flask import Flask, request, Response
from werkzeug.utils import secure_filename

from utils.adbUtils import *
from utils.adbUtils import AdbUtils
from utils.osUtils import OsUtils
from utils.thread import GetLogThread

app = Flask(__name__)

# 加载AndroidLogcat设备进程
threads = []
stream_stop = False
root_path = os.path.dirname(__file__)
con = configparser.ConfigParser()
con.read(root_path + "/config.ini", encoding='utf-8')
config = dict(con.items('kafka'))
producer = KafkaProducer(bootstrap_servers=dict(con.items("kafka"))["server"],
                         value_serializer=lambda m: json.dumps(m).encode())
for deviceItem in AdbUtils().getDevicesList(serialName="0"):
    tName = str(deviceItem) + "_logcat"
    thread = GetLogThread(deviceItem,
                          producer,
                          lambda: stream_stop,
                          tName,
                          config
                          )
    thread.start()
    threads.append(thread)

# 开启mitmProxy功能
# OsUtils().proxy("0")


@app.route("/getDevicesList", methods=['GET'])
def getDevicesList():
    return Response(AdbUtils().getDevicesList(serialName="1"), mimetype='application/json')


@app.route("/installApk", methods=['POST'])
def installApk():
    if request.method == "POST":
        if request.json:
            rep = request.json
            return AdbUtils().installApk(installApkUrl=rep["installApkUrl"], serial=rep["serial"])
        elif request.files:
            apkFile = request.files['apkFile']
            serial = request.form["serial"]

            basePath = os.path.dirname(__file__)
            apkPath = os.path.join(basePath, 'static/uploadApk/',
                                   secure_filename(apkFile.filename))
            apkFile.save(apkPath)

            return AdbUtils().installApk(serial=serial, apkPath=apkPath)


@app.route("/setProxy", methods=['POST'])
def setDevicesProxy():
    if request.method == "POST":
        rep = request.json
        return AdbUtils().setProxy(status=rep["status"],
                                   httpProxy=rep["httpProxy"],
                                   serial=rep["serial"],
                                   batch=rep["batch"])


@app.route("/setSensors", methods=["POST"])
def setDeviceAndProxy():
    if request.method == "POST":
        rep = request.json
        global stream_stop
        if rep["status"] == "1":
            stream_stop = False
            return {"status": "proxy on"}
        elif rep["status"] == "0":
            stream_stop = True
            return {"status": "proxy off"}


@app.route("/setClipboard", methods=["POST"])
def setClipboard():
    if request.method == "POST":
        rep = request.json
        return AdbUtils().setClipboard(serial=rep["serial"], batch=rep["batch"], content=rep["content"])


@app.route("/screenshot", methods=["POST"])
def screenshot():
    if request.method == "POST":
        rep = request.json
        return AdbUtils().screenshot(serial=rep["serial"], picPath=rep["picPath"])


if __name__ == '__main__':
    app.run(Process=True)
