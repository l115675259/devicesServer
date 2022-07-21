import threading

from flask import Flask, request
from werkzeug.utils import secure_filename
from uitls.adbUtils import *
from uitls.adbUtils import AdbUtils

# from queue import Queue

app = Flask(__name__)
AndroidLog_threads = AdbUtils().getAndroidLog()

@app.route("/install")
def install():
    body = request.json
    install().installApk(body["installApkUrl"])


@app.route("/getDevicesList", methods=['GET'])
def getDevicesList():
    return str(AdbUtils().getDevicesList(serialName="1"))


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


@app.route("/setDeviceAndProxy", methods=["POST"])
def setDeviceAndProxy():
    if request.method == "POST":
        rep = request.json

        if rep["status"] == "1":
            print(AndroidLog_threads)
            for i in AndroidLog_threads:
                i.start()
            return {"status": "proxy on"}
        elif rep["status"] == "0":
            for i in AndroidLog_threads:
                stop_thread(i)
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
    app.run()
