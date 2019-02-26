#!/usr/bin/env python3
"""Main module for the MCP app."""

import datetime
import json
import logging
import os
import sys
from PyQt5.Qt import QIcon
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QMainWindow, QMenu, QMessageBox,
                             QSystemTrayIcon, QWidget)

from forms import ui_mcp_main_window
from mcp_mqtt import McpMqtt
from mqtt_settings_dialog import MqttSettingsDialog
import resources

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.DEBUG)
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs.txt')
fh = logging.FileHandler(_LOG_FILE)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
fh.setLevel(logging.DEBUG)
logging.root.addHandler(fh)


class MCP(QMainWindow):
    """Main window for the MCP app."""

    _SETTINGS_FILE = 'settings.json'

    def __init__(self, server=None):
        """Create a new MCP window."""
        QWidget.__init__(self, None)
        self._mcp_mqtt = None
        self._notification = None
        self._muted = False
        self._settings = {}
        self._green_icon = QIcon(resources.GREEN_ICON)
        self._red_icon = QIcon(resources.RED_ICON)
        self.ui = ui_mcp_main_window.Ui_McpMainWindow()
        self.ui.setupUi(self)
        screenFrame = self.frameGeometry()
        screenFrame.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(screenFrame.topLeft())
        self.ui.statusBar
        self.ui.statusBar.showMessage("Disconnected")
        # Tray Icon
        menu = QMenu()
        mute_button = menu.addAction('Mute', self.mute)
        menu.addAction('Exit', self.quit)
        mute_button.setCheckable(True)
        self._mute_button = mute_button
        self._tray = QSystemTrayIcon(self._green_icon)
        self._tray.setContextMenu(menu)
        self._tray.show()
        # Signals and Slots
        self._tray.activated.connect(self._handle_tray_clicked)
        self._tray.messageClicked.connect(self._clear_current_notification)
        self.ui.connectButton.clicked.connect(self._handle_connect_clicked)
        self.ui.sendMessageButton.clicked.connect(self._handle_send_message_clicked)
        self.ui.listSmsButton.clicked.connect(self._handle_list_sms_clicked)
        self.ui.editServerButton.clicked.connect(self._handle_edit_server_clicked)
        self.ui.mqttServerEdit.textChanged.connect(self._handle_server_text_changed)
        # Other Initialization
        self._load_settings()

    def closeEvent(self, event):
        self._save_settings()
        event.accept()

    def mute(self):
        """Mute pop-up notifications."""
        self._muted = self.sender().isChecked()

    def quit(self):
        """Close the MCP UI."""
        if self._mcp_mqtt:
            self._mcp_mqtt.disconnect()
        QApplication.quit()

    def _save_settings(self):
        self._settings['ui'] = {
            'muted': self._muted,
            'recepient': self.ui.recepientEdit.text().strip(),
        }
        with open(MCP._SETTINGS_FILE, 'w') as f:
            json.dump(self._settings, f, indent=4)

    def _load_settings(self):
        try:
            with open(MCP._SETTINGS_FILE, 'r') as f:
                self._settings = json.load(f)
                self.ui.mqttServerEdit.setText(self._settings.get('mqtt_server', ''))
                ui_settings = self._settings.get('ui')
                muted = ui_settings.get('muted', False)
                recepient = ui_settings.get('recepient', '')
                self._mute_button.setChecked(muted)
                self._muted = muted
                self.ui.recepientEdit.setText(recepient)
        except (OSError, json.decoder.JSONDecodeError, TypeError):
            pass

    def _handle_edit_server_clicked(self):
        settings = MqttSettingsDialog(self._settings).edit_settings()
        if settings:
            self._settings = settings
            self._save_settings()
            self.ui.mqttServerEdit.setText(self._settings.get('mqtt_server', ''))

    def _handle_server_text_changed(self, text):
        self.ui.connectButton.setEnabled(len(text) > 0)

    def _handle_tray_clicked(self, reason):
        if reason != QSystemTrayIcon.Trigger:
            return
        if self._notification:
            self._show_message(self._notification, force=True)
        else:
            self.setVisible(not self.isVisible())

    def _clear_current_notification(self):
        self._notification = None
        self._tray.setIcon(self._green_icon)

    def _show_message(self, message, force=False):
        self._notification = message
        self._tray.setIcon(self._red_icon)
        if not self._muted or force:
            self._tray.showMessage('MCP', message, QSystemTrayIcon.Information)

    def _handle_connect_clicked(self):
        mqtt_host = self._settings.get('mqtt_server', '').strip()
        mqtt_ip, mqtt_port = (mqtt_host + ':1883').split(':')[0:2]
        mqtt_port = int(mqtt_port)
        client_id = self._settings.get('client_id', '').strip()
        error_msg = None
        if not mqtt_host:
            error_msg = 'MQTT Host is empty!'
        elif not mqtt_port:
            error_msg = 'MQTT port is empty!'
        elif not client_id:
            error_msg = 'Client ID is empty'
        if error_msg:
            QMessageBox.critical(self, self.windowTitle(), error_msg)
            return
        auth_settings = self._settings.get('authentication', {})
        use_username = auth_settings.get('use_username')
        username = auth_settings.get('username') if use_username else None
        password = auth_settings.get('password') if use_username else None
        self._mcp_mqtt = McpMqtt(mqtt_ip, mqtt_port, client_id, username, password)
        self._mcp_mqtt.connect_message.connect(self._handle_connect_message)
        self._mcp_mqtt.log_message.connect(self._handle_log_message)
        self._mcp_mqtt.new_sms_message.connect(self._handle_new_sms_message)
        self._mcp_mqtt.run()

    def _handle_send_message_clicked(self):
        if self._mcp_mqtt:
            number = self.ui.recepientEdit.text().strip()
            message = self.ui.messageEdit.toPlainText().strip()
            self._mcp_mqtt.send_sms(number, message)
            self.ui.messageEdit.clear()

    def _handle_list_sms_clicked(self):
        if self._mcp_mqtt:
            self._mcp_mqtt.list_sms()

    def _handle_connect_message(self, connected):
        status = 'Connected' if connected else 'Disconnected'
        date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        message = '{0}: {1}'.format(status, date_str)
        self._show_message(message)
        self.ui.statusBar.showMessage(message)
        self.ui.listSmsButton.setEnabled(connected)
        self.ui.sendMessageButton.setEnabled(connected)

    def _handle_log_message(self, date, message):
        log_message = '%s: %s\n' % (date, message)
        self.ui.logMessagesEdit.moveCursor(QTextCursor.End)
        self.ui.logMessagesEdit.insertPlainText(log_message)
        self.ui.logMessagesEdit.moveCursor(QTextCursor.End)

    def _handle_new_sms_message(self, date, number, message):
        self._show_message(message)
        self._handle_log_message(date, 'New SMS from %s: %s' % (number, message))


def _main():
    app = QApplication(sys.argv)
    mcp = MCP()
    mcp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    _main()
