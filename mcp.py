#!/usr/bin/env python3
"""Main module for the MCP app."""

import logging
import sys
from PyQt5.QtCore import QTimer
from PyQt5.QtGui import QTextCursor
from PyQt5.QtWidgets import QMainWindow, QWidget, QApplication, QDesktopWidget
from forms import ui_mcp_main_window
from mcp_mqtt import McpMqtt

logging.basicConfig(format='%(asctime)s:%(levelname)s:%(message)s',
                    datefmt='%Y-%m-%d %H:%M:%S',
                    level=logging.INFO)


class MCP(QMainWindow):
    """Main window for the MCP app."""

    _PING_INTERVAL = 10000
    _mcp_mqtt = None
    _ping_timer = None

    def __init__(self, server=None):
        """Create a new MCP window."""
        QWidget.__init__(self, None)
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
        # Signals and Slots
        self.ui.connectButton.clicked.connect(self._handle_connect_clicked)
        self.ui.sendMessageButton.clicked.connect(self._handle_send_message_clicked)
        self._ping_timer.timeout.connect(self._handle_ping_timeout)

    def _handle_ping_timeout(self):
        if self._mcp_mqtt:
            self._mcp_mqtt.send_ping()

    def _handle_connect_clicked(self):
        # TODO Get values from UI
        self._mcp_mqtt = McpMqtt('127.0.0.1', 1883, 'mchecca')
        self._mcp_mqtt.ping_message.connect(self._handle_ping_message)
        self._mcp_mqtt.log_message.connect(self._handle_log_message)
        self._mcp_mqtt.run()

    def _handle_send_message_clicked(self):
        number = self.ui.recepientEdit.text().strip()
        message = self.ui.messageEdit.toPlainText().strip()
        self._mcp_mqtt.send_sms(number, message)

    def _handle_ping_message(self, date):
        self.ui.statusBar.showMessage('Connected: %s' % date)

    def _handle_log_message(self, date, message):
        log_message = '%s: %s\n' % (date, message)
        self.ui.logMessagesEdit.moveCursor(QTextCursor.End)
        self.ui.logMessagesEdit.insertPlainText(log_message)
        self.ui.logMessagesEdit.moveCursor(QTextCursor.End)


def _main():
    app = QApplication(sys.argv)
    mcp = MCP()
    mcp.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    _main()
