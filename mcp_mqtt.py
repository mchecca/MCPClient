"""MCP MQTT Client module."""

import datetime
import json
import logging

from PyQt5.QtCore import QObject, pyqtSignal
import paho.mqtt.client as mqtt

_SEND_TOPIC_FMT = "%s/sms/send"
_RECEIVE_TOPIC_FMT = '%s/sms/receive'
_EVENT_TOPIC_FMT = "%s/sms/event"
_PING_TOPIC_FMT = "%s/ping"


class McpMqtt(mqtt.Client, QObject):
    """MQTT Client for MCP."""

    log_message = pyqtSignal(datetime.datetime, str, name='logMessage')
    ping_message = pyqtSignal(datetime.datetime, name='pingMessage')
    new_sms_message = pyqtSignal(datetime.datetime, str, str, name='newSmsMessage')
    _mqtt_ip = None
    _mqtt_port = None
    _client_id = None

    def __init__(self, mqtt_ip, mqtt_port, client_id):
        """Initialize the MQTT handler."""
        super(McpMqtt, self).__init__(client_id=client_id, clean_session=False, transport="tcp")
        QObject.__init__(self)
        self._mqtt_ip = mqtt_ip
        self._mqtt_port = mqtt_port
        self._client_id = client_id

    def on_connect(self, client, userdata, flags, rc):
        """Handle MQTT connection established."""
        del client, userdata, flags, rc
        event_topic = _EVENT_TOPIC_FMT % self._client_id
        receive_topic = _RECEIVE_TOPIC_FMT % self._client_id
        self.subscribe([(event_topic, 0), (receive_topic, 0)])
        self.message_callback_add(event_topic, self._handle_event_message)
        self.message_callback_add(receive_topic, self._handle_receive_message)
        self.send_ping()

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
        self.connect_async(self._mqtt_ip, self._mqtt_port)
        self.loop_start()

    def send_ping(self):
        """Send a ping to the MCP client."""
        ping_topic = _PING_TOPIC_FMT % self._client_id
        self.publish(ping_topic, '')

    def send_sms(self, number, message):
        """Send a command to MCP to send an SMS."""
        msg = {'number': number, 'message': message}
        send_topic = _SEND_TOPIC_FMT % self._client_id
        self.publish(send_topic, json.dumps(msg))

    def _handle_event_message(self, client, userdata, msg):
        """Run message callback when an event message is received."""
        del client, userdata
        try:
            msg_json = json.loads(msg.payload)
            date = datetime.datetime.fromtimestamp(int(msg_json['date']))
            if msg_json['type'] == 'ping':
                self.ping_message.emit(date)
            elif msg_json['type'] == 'sms_sent':
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
