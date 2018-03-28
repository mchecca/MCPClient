# MCP
This is the client application for MCP. The logic is implemented in Python and uses PyQt.

### Compiling
Run `make` from the top level to generate the forms code.

### Running
After compiling, just run `mcp.py`
Settings will be saved to `settings.json` and a log file will be written to `logs.txt`, both in the current directory.

### Configuration
MCP needs to be able to reach an MQTT broker. The MQTT configuration page allows you to set the hostname, port, and optionally username/password for the MQTT connection.
