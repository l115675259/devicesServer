import configparser
import os
import re
import time
import typing

import adbutils
import apkutils2
import requests
from adbutils import AdbInstallError
from adbutils._adb import BaseClient
from adbutils._device import AdbDevice
from adbutils._utils import ReadProgress, humanize
from retry import retry


class AdbDevices(AdbDevice):

    def __init__(self, client: BaseClient, serial: str = None, transport_id: int = None):
        super().__init__(client=client, serial=serial, transport_id=transport_id)

    @retry(BrokenPipeError, delay=5.0, jitter=[3, 5], tries=3)
    def install(self,
                path_or_url: str,
                nolaunch: bool = False,
                uninstall: bool = False,
                silent: bool = False,
                callback: typing.Callable[[str], None] = None):
        """
        Install APK to device

        Args:
            path_or_url: local path or http url
            nolaunch: do not launch app after install
            uninstall: uninstall app before install
            silent: disable log message print
            callback: only two event now: <"BEFORE_INSTALL" | "FINALLY">

        Raises:
            AdbInstallError, BrokenPipeError
        """
        if re.match(r"^https?://", path_or_url):
            resp = requests.get(path_or_url, stream=True)
            resp.raise_for_status()
            length = int(resp.headers.get("Content-Length", 0))
            r = ReadProgress(resp.raw, length)
            print("tmpfile path:", r.filepath())
        else:
            length = os.stat(path_or_url).st_size
            fd = open(path_or_url, "rb")
            r = ReadProgress(fd, length, source_path=path_or_url)

        def _dprint(*args):
            if not silent:
                print(*args)

        dst = "/data/local/tmp/tmp-%d.apk" % (int(time.time() * 1000))
        _dprint("push to %s" % dst)

        start = time.time()
        self.sync.push(r, dst)

        # parse apk package-name
        apk = apkutils2.APK(r.filepath())
        package_name = apk.manifest.package_name
        main_activity = apk.manifest.main_activity
        if main_activity and main_activity.find(".") == -1:
            main_activity = "." + main_activity

        version_name = apk.manifest.version_name
        _dprint("packageName:", package_name)
        _dprint("mainActivity:", main_activity)
        _dprint("apkVersion: {}".format(version_name))
        _dprint("Success pushed, time used %d seconds" % (time.time() - start))

        new_dst = "/data/local/tmp/{}-{}.apk".format(package_name,
                                                     version_name)
        self.shell(["mv", dst, new_dst])

        dst = new_dst
        info = self.sync.stat(dst)
        print("verify pushed apk, md5: %s, size: %s" %
              (r._hash, humanize(info.size)))
        assert info.size == r.copied

        if uninstall:
            _dprint("Uninstall app first")
            self.uninstall(package_name)

        _dprint("install to android system ...")
        try:
            start = time.time()
            if callback:
                callback("BEFORE_INSTALL")

            self.install_remote(dst, clean=True)
            _dprint("Success installed, time used %d seconds" %
                    (time.time() - start))
            if not nolaunch:
                _dprint("Launch app: %s/%s" % (package_name, main_activity))
                self.app_start(package_name, main_activity)

        except AdbInstallError as e:
            if e.reason in [
                "INSTALL_FAILED_PERMISSION_MODEL_DOWNGRADE",
                "INSTALL_FAILED_UPDATE_INCOMPATIBLE",
                "INSTALL_FAILED_VERSION_DOWNGRADE"
            ]:
                _dprint("uninstall %s because %s" % (package_name, e.reason))
                self.uninstall(package_name)
                self.install_remote(dst, clean=True)
                _dprint("Success installed, time used %d seconds" %
                        (time.time() - start))
                if not nolaunch:
                    _dprint("Launch app: %s/%s" %
                            (package_name, main_activity))
                    self.app_start(package_name, main_activity)
                    # self.shell([
                    #     'am', 'start', '-n', package_name + "/" + main_activity
                    # ])
            elif e.reason == "INSTALL_FAILED_CANCELLED_BY_USER":
                _dprint("Catch error %s, reinstall" % e.reason)
                self.install_remote(dst, clean=True)
                _dprint("Success installed, time used %d seconds" %
                        (time.time() - start))
            else:
                # print to console
                print(
                    "Failure " + e.reason + "\n" +
                    "Remote apk is not removed. Manually install command:\n\t"
                    + "adb shell pm install -r -t " + dst)
                raise
        finally:
            if callback:
                callback("FINALLY")

            return {"tmpFilePath": r.filepath(),
                    "apkInfo": {"mainActivity": main_activity,
                                "permissions": apk.manifest.permissions,
                                "packName": package_name,
                                "versionCode": apk.manifest.version_code,
                                "versioName": version_name,
                                "apkPath": apk.apk_path
                                }
                    }


class AdbUtils:

    def __init__(self):
        self.root_path = os.path.dirname(__file__)[0:-5]

        # 本地配置
        self.con = configparser.ConfigParser()
        self.con.read(self.root_path + "/config.ini", encoding='utf-8')
        self.config = dict(self.con.items('adbUtils'))

        # adb配置
        self.adb = adbutils.AdbClient(host=str(self.config["adb_hosts"]), port=int(self.config["adb_port"]))

    def getDevice(self, serial: str = None):
        """
            获取设备驱动
        """
        if serial is not None:
            return AdbDevices(
                client=BaseClient(host=str(self.config["adb_hosts"]), port=int(self.config["adb_port"])),
                serial=serial)
        if serial is None:
            return self.adb.device_list()[0]

    def getDevicesList(self):
        """
            获取设备列表
        """
        ds = self.adb.device_list()
        if len(ds) == 0:
            return "Can't find any android device/emulator"
        if len(ds) >= 1:
            return ds

    def downloadApk(self, fileName, installApkUrl):
        pathName = self.root_path + "/static/apk" + fileName
        with open(pathName, "wb") as code:
            code.write(installApkUrl.content)

    def installApk(self, serial: str = None, installApkUrl: str = None, apkPath=None):

        apkInfo = None
        device = self.getDevice(serial=serial)

        if installApkUrl is not None:
            apkInfo = device.install(installApkUrl, nolaunch=True, uninstall=False)
        elif apkPath is not None:
            apkInfo = device.install(apkPath, nolaunch=True, uninstall=False)

        if apkInfo["apkInfo"]["packName"] in device.list_packages():
            return apkInfo
        else:
            return "未找到pack"

    def setProxy(self, status: bool, httpProxy: str, serial: str = "0", batch: bool = False):
        """
            设置设备代理服务
        """

        batchResults = {}

        if serial != "0" and batch == "1":
            return "需指定serial或batch批量执行，二者择其一"
        if serial == "0" and batch == "0":
            return "需指定serial或batch批量执行，二者择其一"

        def openProxy(device):
            if status == "1":
                device.shell(f"settings put global http_proxy {httpProxy}")
            elif status == "0":
                device.shell(f"settings put global http_proxy :0")
            return device.shell("settings get global http_proxy")

        if batch == "0":
            batchResults[str(self.getDevice(serial=serial))] = openProxy(self.getDevice(serial=serial))
        elif batch == "1":
            for deviceItem in self.getDevicesList():
                batchResults[str(deviceItem)] = openProxy(deviceItem)

        return batchResults
