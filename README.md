# HTTP request to MQTT message relay/proxy
Simple web server that relays HTTP requests to MQTT messages.   

I needed some relay function that translates a HTTP request into an MQTT message. This can be used to send messages from environments and appliances where MQTT support is not readily available, e.g. on a basic router or environment where you can't easily install libraries or dependencies but utilities like curl or wget are available for making HTTP requests.   

## Use cases
I use it to send router alerts and events (e.g. on new VPN client connection or on uplink down). Sending HTTP requests using curl is easy but wget or even a web browser would work too. Example of a curl request:   
`curl -s http://host:8234/topic/message`   

Ensure to URL encode the topic and message if the tool you use does not do this by default. E.g.:   
`curl -s http://host:8234/source%2Ftopic/my%20message`   

## Installation
Run the following commands to install the script and dependencies. Currently, only the Paho MQTT Python client library is required:
```
git clone https://github.com/fwpt/http2mqtt.git
cd http2mqtt
pip install paho-mqtt
```

## Configuration
The following settings can be configured in the script:   
| Variable  | Description           |
| --------: |---------------------- |
| HTTP_HOST | Host/ip/interface to bind to or empty to bind to all interfaces (0.0.0.0) | 
| HTTP_PORT | TCP port where the web service is exposed, default 8234 |
| MQTT_HOST | MQTT broker ip/hostname, export MQTT_HOST=host or default to localhost |
| MQTT_PORT | MQTT broker port, default 1883 |
| MQTT_USER | MQTT username, export MQTT_USER=username if required |
| MQTT_PASS | MQTT password - do not store passwords in scripts, export MQTT_PASS=password if required |
| MQTT_CLIENTID | MQTT client identifier, set to your unique client id |
| VALID_TOPICS | Whitelist of valid MQTT topic to publish to or empty list to skip validation |
| TOPIC_PREFIX | Default topic prefix or empty when not required |
| MAX_MESSAGE_LEN | Maximum length of the MQTT message payload, default 100 (not tested with other values) |

## Usage
```
Usage: http2mqtt.py [-h] [--log LOG]

Simple web server that relays HTTP requests to MQTT messages.

optional arguments:
  -h, --help  show this help message and exit
  --log LOG   set logging mode: ERROR (default), WARN, INFO, DEBUG
```

Normally, it is advised to run this script as a service in your Linux environment. This can be done using the following steps in most modern Linux environments, including Ubuntu.

### Create the service
Create a new file in `/etc/systemd/system/http2mqtt@user.service` with the following contents:
```
[Service]
Type=simple
User=%i
WorkingDirectory=/path/to/script/http2mqtt
ExecStart=/usr/bin/python3 /path/to/script/http2mqtt/http2mqtt.py
Restart=on-failure
RestartSec=5s

[Install]
WantedBy=multi-user.target
```
Restart the systemctl daemon: `sudo systemctl daemon-reload`   
Enable the service on system start: `sudo systemctl enable http2mqtt@user.service`   
Start the service now: `sudo systemctl start http2mqtt@user.service`    

The web server should not be running on the configured port. 

## Limitations
This is currently a basic implementation with no support for TLS (HTTPS) or authentication. While I do not plan to implement such features, the script can be extended easily to cater for this.  

A basic topic whitelist is implemented along with some very basic validation on the topic and message string format. This implementation is not suitable to be exposed to the internet. 

**Topic format**: MQTT topic should only contain printable ASCII characters, no spaces.   
**Message format**: I only need a-Z, 0-9 and some special characters like space, dot, (, ), -, _ for my use-case but feel free to adapt if required. Message length is also set to maximum 100 characters at the moment.   
