import os

from flask import Flask, request
from werkzeug.utils import secure_filename

from uitls.adbUtils import AdbUtils

app = Flask(__name__)


@app.route('/')
def hello_world():  # put application's code here
    return "hello"


@app.route("/install")
def install():
    body = request.json
    install().installApk(body["installApkUrl"])


@app.route("/getDevicesList", methods=['GET'])
def getDevicesList():
    return str(AdbUtils().getDevicesList())


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


if __name__ == '__main__':
    app.run()
