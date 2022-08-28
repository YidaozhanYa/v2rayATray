#!/usr/bin/env python3

# 2022 YidaozhanYa 

import sys
from PyQt5.QtWidgets import QMenu, QWidget, QAction, QSystemTrayIcon, QApplication, QMessageBox, QInputDialog
from PyQt5.QtCore import QThread, pyqtSignal
from PyQt5.QtGui import QIcon

import os
import sys
from functools import partial
import json
import time
import requests
import subprocess

config_folder: str = os.environ.get('HOME') + '/.config/v2raya_tray'
if not os.path.exists(config_folder):
    os.mkdir(config_folder)


# 可复用的代码
def add_latency(action, ping_latency):
    if ping_latency != '':
        if ping_latency.endswith('ms'):
            latency = int(ping_latency.replace('ms', ''))
            if latency < 400:
                action.setIcon(QIcon.fromTheme('nm-signal-100-symbolic'))
            elif latency < 1000:
                action.setIcon(QIcon.fromTheme('nm-signal-75-symbolic'))
            elif latency < 2000:
                action.setIcon(QIcon.fromTheme('nm-signal-50-symbolic'))
            else:
                action.setIcon(QIcon.fromTheme('nm-signal-25-symbolic'))
            action.setText(action.text() + ' | ' + ping_latency)
        else:
            action.setIcon(QIcon.fromTheme('cancel'))


def notify_send(short_message: str):
    subprocess.Popen(['notify-send', '-i', 'v2raya', '-a', 'v2rayA 系统托盘', short_message])


class V2rayAClass(object):
    def __init__(self, url: str):
        self.url: str = url
        self.version: str = requests.get(self.url + "/api/version").json()['data']['version']
        self.token: str = ''
        self.running: bool = False
        self.servers = None
        self.connected_server = None
        self.subscriptions = None

    def login(self, username: str, password: str):
        auth_data = {"username": username, "password": password}
        open(config_folder + '/auth.json', 'w').write(json.dumps(auth_data))
        self.token = requests.post(self.url + "/api/login", json=auth_data).json()['data']['token']

    def touch(self):
        data = requests.get(self.url + "/api/touch", headers={"Authorization": self.token}).json()['data']
        self.running: bool = data['running']
        self.update_touch(data['touch'])

    def update_touch(self, touch):
        self.servers = touch['servers']
        self.subscriptions = touch['subscriptions']
        try:
            self.connected_server = touch['connectedServer'][0]
        except Exception:
            QMessageBox.warning(None, '启动失败', '请先在 v2rayA 网页控制台中选择一个节点。', QMessageBox.Yes,
                                QMessageBox.Yes)
            app.quit()
            sys.exit()

    def connect_server(self, server: int):
        server_data = {'_type': 'server', 'outbound': 'proxy', 'id': server}
        response = requests.post(self.url + "/api/connection", json=server_data,
                                 headers={"Authorization": self.token}).json()
        if response['code'] == "SUCCESS":
            return True
        else:
            QMessageBox.warning(None, '连接失败', response['message'], QMessageBox.Yes, QMessageBox.Yes)
            return False

    def connect_subscription_server(self, server: int, sub: int):
        server_data = {'_type': 'subscriptionServer', 'outbound': 'proxy', 'id': server, 'sub': sub}
        response = requests.post(self.url + "/api/connection", json=server_data,
                                 headers={"Authorization": self.token}).json()
        if response['code'] == "SUCCESS":
            return True
        else:
            QMessageBox.warning(None, '连接失败', response['message'], QMessageBox.Yes, QMessageBox.Yes)
            return False

    def start_v2ray(self):
        response = requests.post(self.url + "/api/v2ray", headers={"Authorization": self.token}).json()
        self.running = True
        self.update_touch(response['data']['touch'])

    def stop_v2ray(self):
        response = requests.delete(self.url + "/api/v2ray", headers={"Authorization": self.token}).json()
        self.running = False
        self.update_touch(response['data']['touch'])

    def update_subscription(self, sub: int):
        response = requests.put(self.url + "/api/subscription", json={'_type': 'subscription', 'id': sub},
                                headers={"Authorization": self.token}).json()
        self.running = response['data']['running']
        self.update_touch(response['data']['touch'])

    def test_httplatency(self):
        list_servers = []
        for i in range(1, len(self.servers) + 1):
            list_servers.append({'id': i, '_type': 'server', 'sub': None})
        requests.get(self.url + "/api/httpLatency", params={'whiches': json.dumps(list_servers)},
                     headers={"Authorization": self.token}).json()

    def test_sub_httplatency(self, sub: int):
        list_servers = []
        for i in range(1, len(self.subscriptions[sub]['servers']) + 1):
            list_servers.append({'id': i, '_type': 'subscriptionServer', 'sub': sub})
        requests.get(self.url + "/api/httpLatency", params={'whiches': json.dumps(list_servers)},
                     headers={"Authorization": self.token}).json()


v2rayA = V2rayAClass("http://localhost:2017")


class TrayIcon(QSystemTrayIcon):
    def __init__(self, parent=None):
        super(TrayIcon, self).__init__(parent)
        # 预先定义好，不是动态更新的action
        self.titleAction = QAction("v2rayA v" + v2rayA.version)
        self.titleAction.setIcon(QIcon.fromTheme('v2raya'))

        # 应付pycharm用的
        self.server_menu = None
        self.tmp_menu = {}
        self.current_action = None

        # 线程
        self.select_server_work = None
        self.select_sub_server_work = None
        self.icon_anim_work = None
        self.start_stop_v2ray_work = None
        self.update_subscription_work = None
        self.test_latency_work = None
        self.test_sub_latency_work = None
        self.test_httplatency_work = None
        self.test_sub_httplatency_work = None

        if not os.path.exists(config_folder + '/auth.json'):
            username, password = None, None
            ok = False
            while not ok:
                username, ok = QInputDialog.getText(parent, "登录", "请输入 v2rayA 用户名")
            ok = False
            while not ok:
                password, ok = QInputDialog.getText(parent, "登录", "请输入 v2rayA 密码")
            v2rayA.login(username=username, password=password)
        else:
            auth_data = json.loads(open(config_folder + '/auth.json', 'r').read())
            v2rayA.login(username=auth_data['username'], password=auth_data['password'])
        self.make_menu()
        self.other()

    def make_menu(self):
        v2rayA.touch()
        menu = QMenu()

        self.current_action = None

        # tooltip
        self.setToolTip("v2rayA v" + v2rayA.version + '\n')
        # 独立节点菜单
        self.server_menu = QMenu()
        self.server_menu.setTitle('独立节点')
        self.server_menu.setIcon(QIcon.fromTheme('preferences-system-network-proxy-symbolic'))

        tmp_action = QAction('测试真连接延迟', self,
                             triggered=partial(self.test_httplatency))
        tmp_action.setIcon(QIcon.fromTheme('office-chart-bar-stacked'))
        self.server_menu.addAction(tmp_action)
        self.server_menu.addSeparator()

        for server in v2rayA.servers:
            tmp_action = QAction(server['name'], self, triggered=partial(self.select_server, server['id']))
            add_latency(action=tmp_action, ping_latency=server['pingLatency'])
            if v2rayA.connected_server['_type'] == 'server' \
                    and v2rayA.connected_server['id'] == server['id']:
                tmp_action.setIcon(QIcon.fromTheme('network-connect'))
                print('正在使用的节点是 ' + server['name'])
                self.current_action = QAction(server['name'], self, triggered=self.start_stop_v2ray)
                self.setToolTip(self.toolTip() + tmp_action.text())
                if v2rayA.running:
                    self.current_action.setIcon(QIcon.fromTheme('gtk-connect'))
                else:
                    self.current_action.setIcon(QIcon.fromTheme('gtk-disconnect'))
            self.server_menu.addAction(tmp_action)

        # 订阅列表

        for subscription in v2rayA.subscriptions:
            self.tmp_menu[subscription['id']] = QMenu()
            if 'remarks' in subscription:
                self.tmp_menu[subscription['id']].setTitle(subscription['remarks'])
            else:
                self.tmp_menu[subscription['id']].setTitle(subscription['host'])
            #self.tmp_menu[subscription['id']].setIcon(QIcon.fromTheme('application-rss+xml-symbolic'))

            tmp_action = QAction('更新订阅', self,
                                 triggered=partial(self.update_subscription, subscription['id']))
            tmp_action.setIcon(QIcon.fromTheme('poedit-update'))
            self.tmp_menu[subscription['id']].addAction(tmp_action)

            tmp_action = QAction('测试真连接延迟', self,
                                 triggered=partial(self.test_sub_httplatency, subscription['id'] - 1))
            tmp_action.setIcon(QIcon.fromTheme('office-chart-bar-stacked'))
            self.tmp_menu[subscription['id']].addAction(tmp_action)

            self.tmp_menu[subscription['id']].addSeparator()

            for server in subscription['servers']:
                server_name = server['name']
                tmp_action = QAction(server_name, self,
                                     triggered=partial(self.select_sub_server, server['id'], subscription['id'] - 1))
                if 'remarks' in subscription:
                    server_name = tmp_action.text().replace(subscription['remarks'].split(' ')[0], '').strip(' |,-—:')
                    tmp_action.setText(server_name)
                add_latency(action=tmp_action, ping_latency=server['pingLatency'])
                if v2rayA.connected_server['_type'] == 'subscriptionServer' \
                        and v2rayA.connected_server['id'] == server['id'] \
                        and v2rayA.connected_server['sub'] == subscription['id'] - 1:
                    tmp_action.setIcon(QIcon.fromTheme('network-connect'))
                    print('正在使用的节点是 ' + server_name)
                    self.setToolTip(self.toolTip() + tmp_action.text())
                    self.current_action = QAction(server_name, self, triggered=self.start_stop_v2ray)
                    if v2rayA.running:
                        self.current_action.setIcon(QIcon.fromTheme('gtk-connect'))
                    else:
                        self.current_action.setIcon(QIcon.fromTheme('gtk-disconnect'))
                self.tmp_menu[subscription['id']].addAction(tmp_action)

        open_web_action = QAction("打开网页控制台", self, triggered=self.open_web)
        open_web_action.setIcon(QIcon.fromTheme('go-jump'))

        quit_action = QAction("退出", self, triggered=self.quit_app)
        quit_action.setIcon(QIcon.fromTheme('exit'))

        menu.addAction(self.titleAction)
        menu.addAction(self.current_action)
        menu.addSeparator()
        menu.addMenu(self.server_menu)
        menu.addSeparator()
        for subscription_menu in self.tmp_menu:
            menu.addMenu(self.tmp_menu[subscription_menu])
        menu.addSeparator()
        menu.addAction(open_web_action)
        menu.addAction(quit_action)

        self.setContextMenu(menu)
        print("菜单加载完毕。")

    def other(self):
        self.activated.connect(self.icon_click)
        # 把鼠标点击图标的信号和槽连接
        if v2rayA.running:
            self.setIcon(QIcon.fromTheme('network-vpn'))
        else:
            self.setIcon(QIcon.fromTheme('network-vpn-disconnected-symbolic'))
        # self.icon = self.MessageIcon()
        # 设置图标

    def select_server(self, server_id: int):
        self.icon_anim_work = IconAnimationThread()
        self.icon_anim_work.start()
        self.select_server_work = SelectServerThread(server_id)
        print('尝试连接到独立节点 ' + str(server_id))
        self.select_server_work.connect_result.connect(self.select_server_result)
        self.select_server_work.start()

    def select_server_result(self, connect_result):
        if connect_result:
            self.make_menu()
        self.icon_anim_work.stop_anim()

    def select_sub_server(self, server_id: int, sub_id: int):
        self.icon_anim_work = IconAnimationThread()
        self.icon_anim_work.start()
        self.select_sub_server_work = SelectSubServerThread(server_id, sub_id)
        print('尝试连接到订阅节点 ' + str(sub_id) + ':' + str(server_id))
        self.select_sub_server_work.connect_result.connect(self.select_sub_server_result)
        self.select_sub_server_work.start()

    def select_sub_server_result(self, connect_result):
        if connect_result:
            self.make_menu()
        self.icon_anim_work.stop_anim()

    def start_stop_v2ray(self):
        self.icon_anim_work = IconAnimationThread()
        self.icon_anim_work.start()
        self.start_stop_v2ray_work = StartStopV2rayThread()
        self.start_stop_v2ray_work.start()
        self.start_stop_v2ray_work.result.connect(self.start_stop_v2ray_result)

    def start_stop_v2ray_result(self):
        self.make_menu()
        self.icon_anim_work.stop_anim()

    def update_subscription(self, sub_id_big: int):
        self.icon_anim_work = IconAnimationThread()
        self.icon_anim_work.start()
        self.update_subscription_work = UpdateSubscriptionThread(sub_id_big)
        print('更新订阅 ' + str(sub_id_big))
        self.update_subscription_work.result.connect(self.update_subscription_result)
        self.update_subscription_work.start()

    def update_subscription_result(self):
        self.make_menu()
        self.icon_anim_work.stop_anim()

    def test_httplatency(self):
        self.icon_anim_work = IconAnimationThread()
        self.icon_anim_work.start()
        self.test_httplatency_work = TestHTTPLatencyThread()
        print('测试独立节点真连接延迟')
        self.test_httplatency_work.result.connect(self.test_httplatency_result)
        self.test_httplatency_work.start()

    def test_httplatency_result(self):
        v2rayA.touch()
        self.make_menu()
        self.icon_anim_work.stop_anim()
        notify_send('所有独立节点的真连接延迟测试完成。')

    def test_sub_httplatency(self, sub_id_small: int):
        self.icon_anim_work = IconAnimationThread()
        self.icon_anim_work.start()
        self.test_sub_httplatency_work = TestSubHTTPLatencyThread(sub_id_small)
        print('测试订阅真连接延迟 ' + str(sub_id_small))
        self.test_sub_httplatency_work.result.connect(self.test_sub_httplatency_result)
        self.test_sub_httplatency_work.start()

    def test_sub_httplatency_result(self):
        v2rayA.touch()
        self.make_menu()
        self.icon_anim_work.stop_anim()
        notify_send('订阅的真连接延迟测试完成。')

    @staticmethod
    def icon_click(reason):
        print(reason)
        # 留待备用

    @staticmethod
    def open_web():
        subprocess.Popen(['xdg-open','http://127.0.0.1:2017'])
        
    @staticmethod
    def quit_app():
        app.quit()
        sys.exit()


class SelectServerThread(QThread):
    connect_result = pyqtSignal(bool)

    def __init__(self, server_id: int):
        super().__init__()
        self.server_id = server_id

    def run(self):
        self.connect_result.emit(v2rayA.connect_server(self.server_id))


class SelectSubServerThread(QThread):
    connect_result = pyqtSignal(bool)

    def __init__(self, server_id: int, sub_id: int):
        super().__init__()
        self.server_id = server_id
        self.sub_id = sub_id

    def run(self):
        self.connect_result.emit(v2rayA.connect_subscription_server(self.server_id, self.sub_id))


class StartStopV2rayThread(QThread):
    result = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        if v2rayA.running:
            v2rayA.stop_v2ray()
        else:
            v2rayA.start_v2ray()
        self.result.emit()


class UpdateSubscriptionThread(QThread):
    result = pyqtSignal()

    def __init__(self, sub_id: int):
        super().__init__()
        self.sub_id = sub_id

    def run(self):
        v2rayA.update_subscription(self.sub_id)
        self.result.emit()


class TestSubHTTPLatencyThread(QThread):
    result = pyqtSignal()

    def __init__(self, sub_id_small: int):
        super().__init__()
        self.sub_id_small = sub_id_small

    def run(self):
        v2rayA.test_sub_httplatency(self.sub_id_small)
        self.result.emit()


class TestHTTPLatencyThread(QThread):
    result = pyqtSignal()

    def __init__(self):
        super().__init__()

    def run(self):
        v2rayA.test_httplatency()
        self.result.emit()


class IconAnimationThread(QThread):
    def __init__(self):
        super().__init__()
        self.threadactive = True

    def run(self):
        while True:
            for i in range(1, 12):
                ti.setIcon(QIcon.fromTheme('nm-stage01-connecting' + str(i).zfill(2)))
                time.sleep(0.1)
                if not self.threadactive:
                    break
            if not self.threadactive:
                break

    def stop_anim(self):
        self.threadactive = False
        if v2rayA.running:
            ti.setIcon(QIcon.fromTheme('network-vpn'))
        else:
            ti.setIcon(QIcon.fromTheme('network-vpn-disconnected-symbolic'))


if __name__ == "__main__":
    app = QApplication(sys.argv)
    ti = TrayIcon(None)
    ti.show()
    sys.exit(app.exec_())
