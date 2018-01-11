all: ui_mcp_main_window.py

ui_mcp_main_window.py: mcp_main_window.ui
	pyuic5 mcp_main_window.ui > ui_mcp_main_window.py

clean:
	rm -f ui_mcp_main_window.py
