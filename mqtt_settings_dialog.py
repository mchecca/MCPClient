"""MQTT Settings Dialog module."""

from PyQt5.QtWidgets import QDialog, QWidget

from forms import ui_mcp_mqtt_server_settings


class MqttSettingsDialog(QDialog):
    """MQTT Settings Dialog for MCP."""

    def __init__(self, settings=None):
        """Create a new MCP MQTT Settings Dialog."""
        QWidget.__init__(self, None)
        self.ui = ui_mcp_mqtt_server_settings.Ui_mqttServerSettingsDialog()
        self.ui.setupUi(self)
        settings = settings or {}
        auth_settings = settings.get('authentication', {})
        self.ui.mqttServerEdit.setText(settings.get('mqtt_server', ''))
        self.ui.clientIdEdit.setText(settings.get('client_id', ''))
        self.ui.usernameCheckbox.setChecked(auth_settings.get('use_username', False))
        self.ui.usernameEdit.setText(auth_settings.get('username', ''))
        self.ui.passwordEdit.setText(auth_settings.get('password', ''))

    def edit_settings(self):
        """Show the settings dialog and return a dictionary if accepted, None otherwise."""
        settings = None
        if self.exec_() == QDialog.Accepted:
            settings = {
                'mqtt_server': self.ui.mqttServerEdit.text(),
                'client_id': self.ui.clientIdEdit.text(),
                'authentication': {
                    'use_username': self.ui.usernameCheckbox.isChecked(),
                    'username': self.ui.usernameEdit.text(),
                    'password': self.ui.passwordEdit.text()
                }
            }
        return settings
