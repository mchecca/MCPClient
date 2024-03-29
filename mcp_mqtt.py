"""MCP MQTT Client module."""

import datetime
import json
import logging

from PyQt5.QtCore import QObject, pyqtSignal
import dateutil.parser
import paho.mqtt.client as mqtt

_SEND_TOPIC_FMT = "%s/sms/send"
_RECEIVE_TOPIC_FMT = '%s/sms/receive'
_EVENT_TOPIC_FMT = "%s/sms/event"
_CONNECTED_TOPIC_FMT = "%s/connected"
_RPC_REQUEST_TOPIC_FMT = "%s/rpc/request"
_RPC_RESPONSE_TOPIC_FMT = "%s/rpc/reply"


class McpMqtt(mqtt.Client, QObject):
    """MQTT Client for MCP."""

    log_message = pyqtSignal(datetime.datetime, str, name='logMessage')
    connect_message = pyqtSignal(bool, name='connectMessage')
    new_sms_message = pyqtSignal(datetime.datetime, str, str, name='newSmsMessage')
    _mqtt_ip = None
    _mqtt_port = None
    _client_id = None

    def __init__(self, mqtt_ip, mqtt_port, client_id, username, password):
        """Initialize the MQTT handler."""
        super(McpMqtt, self).__init__(transport="tcp")
        QObject.__init__(self)
        self._mqtt_ip = mqtt_ip
        self._mqtt_port = mqtt_port
        self._client_id = client_id
        self._username = username
        self._password = password

    def on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection established."""
        del client, userdata, flags, rc
        event_topic = _EVENT_TOPIC_FMT % self._client_id
        receive_topic = _RECEIVE_TOPIC_FMT % self._client_id
        connected_topic = _CONNECTED_TOPIC_FMT % self._client_id
        rpc_response_topic = _RPC_RESPONSE_TOPIC_FMT % self._client_id
        self.subscribe([(event_topic, 2), (receive_topic, 2), (connected_topic, 2), (rpc_response_topic, 2)])
        self.message_callback_add(event_topic, self._handle_event_message)
        self.message_callback_add(receive_topic, self._handle_receive_message)
        self.message_callback_add(connected_topic, self._handle_connect_message)
        self.message_callback_add(rpc_response_topic, self._handle_rpc_response_message)

    def on_message(self, client, userdata, msg):
        """Run message callback when a message is received and no other handlers are registered."""
        del client, userdata
        logging.info('Topic: %s, Message: %s', msg.topic, msg.payload)

    def on_log(self, client, userdata, level, string):
        """Run log callback when a log message is received."""
        del client, userdata
        if level == mqtt.MQTT_LOG_DEBUG:
            logging.debug(string)
        elif level == mqtt.MQTT_LOG_ERR:
            logging.error(string)
        elif level == mqtt.MQTT_LOG_INFO or level == mqtt.MQTT_LOG_NOTICE:
            logging.info(string)
        elif level == mqtt.MQTT_LOG_WARNING:
            logging.warn(string)

    def run(self):
        """Run the McpMqtt client."""
        if self._username and self._password:
            self.username_pw_set(self._username, self._password)
        self.connect_async(self._mqtt_ip, self._mqtt_port)
        self.loop_start()

    def send_sms(self, number, message):
        """Send a command to MCP to send an SMS."""
        msg = {'number': number, 'message': message}
        send_topic = _SEND_TOPIC_FMT % self._client_id
        self.publish(send_topic, json.dumps(msg))

    def list_sms(self):
        """Send a RPC request to get the list of SMS messages."""
        msg = {'id': 'list_sms', 'command': 'list sms'}
        rpc_topic = _RPC_REQUEST_TOPIC_FMT % self._client_id
        self.publish(rpc_topic, json.dumps(msg))

    def _handle_connect_message(self, client, userdata, msg):
        """Run message callback when a connection message is received."""
        del client, userdata
        logging.info('Connect message: %s', msg.payload)
        connected = (msg.payload == b'true')
        self.connect_message.emit(connected)

    def _handle_event_message(self, client, userdata, msg):
        """Run message callback when an event message is received."""
        del client, userdata
        try:
            msg_json = json.loads(msg.payload)
            date = datetime.datetime.fromtimestamp(int(msg_json['date']))
            if msg_json['type'] == 'sms_sent':
                sms_sent_msg = 'Sent SMS to %s: %s' % (msg_json['number'], msg_json['message'])
                self.log_message.emit(date, sms_sent_msg)
            else:
                raise Exception('Unknown event type: %s' % msg_json['type'])
        except Exception:
            logging.exception('Unable to parse JSON message')

    def _handle_receive_message(self, client, userdata, msg):
        """Run message callback when a SMS receive message is received."""
        del client, userdata
        try:
            msg_json = json.loads(msg.payload)
            date = datetime.datetime.fromtimestamp(int(msg_json['date']))
            self.new_sms_message.emit(date, msg_json['number'], msg_json['message'])
        except Exception:
            logging.exception('Unable to parse JSON message')

    def _handle_rpc_response_message(self, client, userdata, msg):
        """Run message callback when an RPC response message is received."""
        del client, userdata
        try:
            msg_json = json.loads(msg.payload)
            if msg_json.get('id', '') == 'list_sms':
                messages = msg_json.get('sms', [])
                for m in reversed(messages):
                    mdate = dateutil.parser.parse(m['date'])
                    msgstr = '{0} {1}: {2}'.format(
                        'From' if m['type'] == 'INBOX' else 'To',
                        m['number'], m['message']
                    )
                    self.log_message.emit(mdate, msgstr)

        except Exception:
            logging.exception('Unable to parse JSON message')
