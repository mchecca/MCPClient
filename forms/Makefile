all: ui_mcp_main_window.py ui_mcp_mqtt_server_settings.py

ui_mcp_main_window.py: mcp_main_window.ui
	pyuic5 mcp_main_window.ui > ui_mcp_main_window.py

ui_mcp_mqtt_server_settings.py: mcp_mqtt_server_settings.ui
	pyuic5 mcp_mqtt_server_settings.ui > ui_mcp_mqtt_server_settings.py

clean:
	rm -f ui_mcp_main_window.py
