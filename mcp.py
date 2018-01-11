#!/usr/bin/env python3
"""Main module for the MCP app."""

import logging
import os
import sys
from PyQt5.Qt import QIcon
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import (QApplication, QDesktopWidget, QMainWindow, QMenu, QSystemTrayIcon,
                             QWidget)

from forms import ui_mcp_main_window
from mcp_mqtt import McpMqtt
import resources

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)
_LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'logs.txt')
fh = logging.FileHandler(_LOG_FILE)
formatter = logging.Formatter('%(asctime)s:%(levelname)s:%(message)s', datefmt='%Y-%m-%d %H:%M:%S')
fh.setFormatter(formatter)
fh.setLevel(logging.INFO)
logging.root.addHandler(fh)


class MCP(QMainWindow):
    """Main window for the MCP app."""

    _PING_INTERVAL = 30000
    _mcp_mqtt = None
    _ping_timer = None
    _notification = None
    _green_icon = None
    _red_icon = None

    def __init__(self, server=None):
        """Create a new MCP window."""
        QWidget.__init__(self, None)
        self._green_icon = QIcon(resources.GREEN_ICON)
        self._red_icon = QIcon(resources.RED_ICON)
        self.ui = ui_mcp_main_window.Ui_McpMainWindow()
        self.ui.setupUi(self)
        self._ping_timer = QTimer()
        self._ping_timer.setInterval(self._PING_INTERVAL)
        self._ping_timer.start()
        screenFrame = self.frameGeometry()
        screenFrame.moveCenter(QDesktopWidget().availableGeometry().center())
        self.move(screenFrame.topLeft())
        self.ui.statusBar
        self.ui.statusBar.showMessage("Disconnected")
        # Tray Icon
        menu = QMenu()
        menu.addAction('Exit', self.quit)
        self._tray = QSystemTrayIcon(self._green_icon)
        self._tray.setContextMenu(menu)
        self._tray.show()
        # Signals and Slots
        self._tray.activated.connect(self._handle_tray_clicked)
        self._tray.messageClicked.connect(self._clear_current_notification)
        self.ui.connectButton.clicked.connect(self._handle_connect_clicked)
        self.ui.sendMessageButton.clicked.connect(self._handle_send_message_clicked)
        self._ping_timer.timeout.connect(self._handle_ping_timeout)

    def quit(self):
        """Close the MCP UI."""
        if self._mcp_mqtt:
            self._mcp_mqtt.disconnect()
        QApplication.quit()

    def _handle_tray_clicked(self, reason):
        if reason != QSystemTrayIcon.Trigger:
            return
        if self._notification:
            self._show_message(self._notification)
        else:
            self.setVisible(not self.isVisible())

    def _clear_current_notification(self):
        self._notification = None
        self._tray.setIcon(self._green_icon)

    def _show_message(self, message):
        self._tray.showMessage('MCP', message, QSystemTrayIcon.Information)
        self._notification = message
        self._tray.setIcon(self._red_icon)

    def _handle_ping_timeout(self):
        if self._mcp_mqtt:
            self._mcp_mqtt.send_ping()

    def _handle_connect_clicked(self):
        # TODO Get values from UI
        self._mcp_mqtt = McpMqtt('127.0.0.1', 1883, 'mchecca')
        self._mcp_mqtt.ping_message.connect(self._handle_ping_message)
        self._mcp_mqtt.log_message.connect(self._handle_log_message)
        self._mcp_mqtt.new_sms_message.connect(self._handle_new_sms_message)
        self._mcp_mqtt.run()

    def _handle_send_message_clicked(self):
        number = self.ui.recepientEdit.text().strip()
        message = self.ui.messageEdit.toPlainText().strip()
        self._mcp_mqtt.send_sms(number, message)

    def _handle_ping_message(self, date):
        self.ui.statusBar.showMessage('Connected: %s' % date)

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
