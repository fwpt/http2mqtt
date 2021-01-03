#!/usr/bin/env python3
"""
Simple web server that relays HTTP requests to MQTT messages
Requires the Paho MQTT Python client library: pip install paho-mqtt
"""

from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import unquote
import os
import argparse
import logging
import string
import paho.mqtt.publish as publish

HTTP_HOST = ""                               # host/ip/interface to bind to or empty for all interfaces
HTTP_PORT = 8234                             # TCP port where the web service is exposed
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")  # MQTT broker ip/hostname, export MQTT_HOST=host or default to localhost
MQTT_PORT = 1883                             # MQTT broker port
MQTT_USER = os.environ.get("MQTT_USER", None)  # MQTT username, export MQTT_USER=username if required
MQTT_PASS = os.environ.get("MQTT_PASS", None)  # MQTT password - do not store passwords in scripts, export MQTT_PASS=password if required
MQTT_CLIENTID = "unique_client_id"           # MQTT client identifier, set to your unique client id
VALID_TOPICS = ["test/topic", "topic"]       # whitelist of valid MQTT topic to publish to or empty list to skip validation
TOPIC_PREFIX = f"home/{MQTT_CLIENTID}/"      # default topic prefix or empty when not required
MAX_MESSAGE_LEN = 100                        # maximum length of the MQTT message payload

# Prepare auth dictionary
MQTT_AUTH = None
if MQTT_USER and MQTT_PASS:
    MQTT_AUTH = {'username': MQTT_USER, 'password': MQTT_PASS}


def sanitise(s, whitelist=[]):
    """
    Sanitises untrusted strings, only allowing a whitelist or characters

    Parameters
    ----------
    s : string
        Raw string to be sanitised
    whitelist : set, optional
        Set with characters that are allowed additional to default whitelist
    
    Returns
    -------
    string
        Sanitised string s, only containing characters that are allowed in whitelist
    """
    # Join default whitelist of ASCII letters and digits with supplied whitelist
    whitelist = set(string.ascii_letters + string.digits) | whitelist

    return ''.join([c for c in s if c in whitelist])


class MqServer(BaseHTTPRequestHandler):
    """
    Class that handles incoming HTTP requests
    """

    def do_GET(self):
        """
        Handle incoming HTTP GET requests
        """

        # Default response code is 200 with message OK in case of successfull request
        response_code = 200
        response_msg = "OK"

        # Incoming request is in /topic/message format, so split the path by /        
        logging.info("Handling new HTTP request %s" % self.path)
        path = self.path.split("/", 2)

        # Validate HTTP request
        if len(path) != 3:
            # Unexpected request format
            logging.info("Unexpected request format; path length should be 3 but is %s" % len(path))
            response_code = 403
            response_msg = "Invalid request"
        else:
            # Obtain the topic and message from the request
            # Values will be url decoded, so encode / in topics with %2F
            # Values are validated against whitelist
            topic = sanitise(unquote(path[1]), set("/"))
            msg = sanitise(unquote(path[2]), set(string.punctuation + " "))
            logging.info("Topic   = %s" % topic)
            logging.info("Message = %s" % msg)

            # Validate topic name against whitelist if supplied
            if len(VALID_TOPICS) > 0 and topic not in VALID_TOPICS:
                # Topic not allowed by topic whitelist
                logging.info("Topic not allowed by topic whitelist.")
                response_code = 404
                response_msg = "ERROR: Invalid topic"
            elif len(msg) > MAX_MESSAGE_LEN:
                # Message exceeds maximum defined message length
                logging.info("Message exceeds maximum defined message length.")
                response_code = 406
                response_msg = "ERROR: Invalid message length"
            else:
                # All validations passed
                # Send the MQTT message to specified topic
                topic = TOPIC_PREFIX + topic
                logging.info("Start sending MQTT message.")
                try:
                    # Only connect when we need to send a message as we don't subscribe to any topics
                    # Paho offers the `single` method for this purpose
                    # Using default qos 0 and set the msg to be retained
                    logging.info("Sending MQTT message to broker %s:%s with clientid %s to topic %s" % (MQTT_HOST, MQTT_PORT, MQTT_CLIENTID, topic))
                    publish.single(topic, msg, retain=True, hostname=MQTT_HOST, port=MQTT_PORT, client_id=MQTT_CLIENTID, auth=MQTT_AUTH)
                    
                except: 
                    # Overly broad catch; need to figure out what exception types can occur here
                    logging.error('Failed to connect and/or send MQTT message.')
                    response_code = 500
                    response_msg = "ERROR: MQ failed"

        # Send the HTTP response
        logging.info("Sending HTTP response %s %s" % (response_code, response_msg))
        self.send_response(response_code)
        self.send_header("Content-type", "text/html")
        self.end_headers()
        self.wfile.write(bytes("<html><head><title>MqResponse</title></head>", "utf-8"))
        self.wfile.write(bytes("<body>", "utf-8"))
        self.wfile.write(bytes("%s" % response_msg, "utf-8"))
        self.wfile.write(bytes("</body></html>", "utf-8"))


if __name__ == "__main__":        

    # Parse arguments
    parser = argparse.ArgumentParser(description='Simple web server that relays HTTP requests to MQTT messages.')
    parser.add_argument("--log", help="set logging mode: ERROR (default), WARN, INFO, DEBUG", default="ERROR")
    args = parser.parse_args()

    # Set log level
    log_level = getattr(logging, args.log.upper())
    if not isinstance(log_level, int):
        raise ValueError('Invalid log level: %s' % log_level)
    logging.basicConfig(level=log_level)

    # Run the server
    try:
        # Attempt to start the webserver and provide the request handler
        logging.info("Starting HTTP server on http://%s:%s..." % ("0.0.0.0" if HTTP_HOST == "" else HTTP_HOST, HTTP_PORT))
        webserver = HTTPServer((HTTP_HOST, HTTP_PORT), MqServer)
        logging.info("Server started.")
        webserver.serve_forever()
    except (KeyboardInterrupt, SystemExit):
        # Might need to tweak this to properly stop the server on systemd stop
        logging.error("Server stop request.")
        pass

    # Gracefully shut the server when we reach this (means exception or interrupt)
    webserver.server_close()
    logging.error("Server stopped.")
