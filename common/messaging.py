import logging
import os
import ssl

import paho.mqtt.client as mqtt


class Messaging:
    """This is a wrapper for the mqtt client."""

    def __init__(self, config, subscription=None, on_message=None, clientId=None):
        self.config = config
        self.connected = False  # Attribute to track connection status
        default_host = "localhost"
        default_port = 1883

        self.client = mqtt.Client(clientId) if clientId else mqtt.Client()
        self.client.enable_logger()
        self.client.on_connect = self.on_connect
        self.client.on_disconnect = self.on_disconnect

        if subscription:
            self.client.user_data_set(subscription)

        if on_message:
            self.client.on_message = on_message

        host = str(
            self.config.get("host") or os.getenv("MQTT_SERVER") or default_host
        ).strip()
        port_raw = self.config.get("port") or os.getenv("MQTT_PORT") or default_port

        if not host:
            host = default_host
            logging.info(" !! [MQTT Client] No host provided, using default: %s", host)

        try:
            port = int(port_raw)
        except (TypeError, ValueError):
            port = default_port
            logging.info(
                " !! [MQTT Client] Invalid port provided, using default: %s", port
            )

        ca_cert = self.config.get("ca_cert") or os.getenv("MQTT_CA_CERT")
        certfile = self.config.get("certfile") or os.getenv("MQTT_CERTFILE")
        keyfile = self.config.get("keyfile") or os.getenv("MQTT_KEYFILE")

        wants_tls = (port == 8883) or bool(ca_cert) or bool(certfile) or bool(keyfile)

        # Validate mTLS inputs
        if (certfile and not keyfile) or (keyfile and not certfile):
            raise ValueError(
                "Both certfile and keyfile must be provided for client certificate auth (mTLS)."
            )

        if wants_tls:
            try:
                self.client.tls_insecure_set(False)
                self.client.tls_set(
                    ca_certs=ca_cert or None,
                    certfile=certfile or None,
                    keyfile=keyfile or None,
                    cert_reqs=ssl.CERT_REQUIRED,
                    tls_version=ssl.PROTOCOL_TLS_CLIENT,
                )
                logging.info(
                    " >> [MQTT Client] TLS enabled (%s)",
                    "mTLS" if certfile and keyfile else "server-validated TLS",
                )
            except Exception as e:
                logging.error(" !! [MQTT Client] Failed to configure TLS: %s", e)
                raise
        else:
            logging.info(" >> [MQTT Client] TLS disabled (plain MQTT)")

        username = self.config.get("username") or os.getenv("MQTT_USERNAME")
        password = self.config.get("password") or os.getenv("MQTT_PASSWORD")
        if username:
            self.client.username_pw_set(username, password)

        logging.info(" >> [MQTT Client] Connecting to %s:%s ...", host, port)
        self.client.connect(host, port)

    def publish(self, topic, payload, qos=0, retain=False):
        """Publish a message if the client is connected.

        Raises:
            RuntimeError: if the MQTT client is not connected yet.
            Exception: re-raises any error from the underlying client.publish.
        """
        if not self.connected:
            msg = f"MQTT client is not connected; cannot publish to topic '{topic}'"
            logging.error(" !! [MQTT Client] %s", msg)
            raise RuntimeError(msg)

        try:
            self.client.publish(topic, payload, qos, retain)
        except Exception as e:
            logging.error(" !! [MQTT Client] Error publishing message: %s", str(e))
            raise

    def subscribe(self, topic):
        subscribe_options = mqtt.SubscribeOptions(noLocal=True)
        self.client.subscribe(topic, options=subscribe_options)

    def loop_forever(self):
        self.client.loop_forever()

    def loop_start(self):
        self.client.loop_start()

    def loop_stop(self):
        self.client.loop_stop()

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.connected = True
            logging.info(" >> [MQTT Client] Connected to MQTT Broker")
            if userdata:
                client.subscribe(userdata)
        else:
            self.connected = False
            logging.error(" !! [MQTT Client] Failed to connect, return code %d", rc)

    def on_disconnect(self, client, userdata, rc):
        self.connected = False
        if rc != 0:
            logging.warning(" !! [MQTT Client] Unexpected disconnection (rc=%s)", rc)


def on_message(client, userdata, message):
    pass
