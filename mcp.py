#!/usr/bin/env python3
"""Main module for the MCP app."""

import datetime
import logging
import os
import sys
from PyQt5.Qt import QIcon
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QMainWindow, QMenu, QMessageBox,
                             QSystemTrayIcon, QWidget)

from forms import ui_mcp_main_window
from mcp_mqtt import McpMqtt
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

    def __init__(self, server=None):
        """Create a new MCP window."""
        QWidget.__init__(self, None)
        self._mcp_mqtt = None
        self._notification = None
        self._muted = False
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
        self._tray = QSystemTrayIcon(self._green_icon)
        self._tray.setContextMenu(menu)
        self._tray.show()
        # Signals and Slots
        self._tray.activated.connect(self._handle_tray_clicked)
        self._tray.messageClicked.connect(self._clear_current_notification)
        self.ui.connectButton.clicked.connect(self._handle_connect_clicked)
        self.ui.sendMessageButton.clicked.connect(self._handle_send_message_clicked)

    def mute(self):
        """Mute pop-up notifications."""
        self._muted = self.sender().isChecked()

    def quit(self):
        """Close the MCP UI."""
        if self._mcp_mqtt:
            self._mcp_mqtt.disconnect()
        QApplication.quit()

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
        mqtt_host = self.ui.mqttServerEdit.text().strip()
        mqtt_ip, mqtt_port = (mqtt_host + ':1883').split(':')[0:2]
        mqtt_port = int(mqtt_port)
        client_id = self.ui.clientIdEdit.text().strip()
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
        self._mcp_mqtt = McpMqtt(mqtt_ip, mqtt_port, client_id)
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

    def _handle_connect_message(self, connected):
        status = 'Connected' if connected else 'Disconnected'
        date_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.ui.statusBar.showMessage('%s: %s' % (status, date_str))

    def _handle_log_message(self, date, message):
        self._show_message(message)
        log_message = '%s: %s\n' % (date, message)
        self.ui.logMessagesEdit.moveCursor(QTextCursor.End)
        self.ui.logMessagesEdit.insertPlainText(log_message)
        self.ui.logMessagesEdit.moveCursor(QTextCursor.End)

    def _handle_new_sms_message(self, date, number, message):
        self._handle_log_message(date, 'New SMS from %s: %s' % (number, message))


def _main():
    app = QApplication(sys.argv)
    mcp = MCP()
    mcp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    _main()
