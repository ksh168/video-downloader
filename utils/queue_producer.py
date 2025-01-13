#!/usr/bin/env python
import pika, os, json, uuid, time, ssl
from datetime import datetime

# Get the CloudAMQP URL from environment variable
CLOUDAMQP_URL = os.getenv("CLOUDAMQP_URL")

# Parse the AMQP URL
params = pika.URLParameters(CLOUDAMQP_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()

QUEUE_NAME = os.getenv("QUEUE_NAME")
channel.queue_declare(queue=QUEUE_NAME, durable=True)


def create_connection():
    """Create a new connection for each message"""
    params = pika.URLParameters(CLOUDAMQP_URL)

    # If using amqps
    # if params.ssl:
    #     context = ssl.create_default_context()
    #     context.check_hostname = False
    #     context.verify_mode = ssl.CERT_NONE
    #     params.ssl_options = pika.SSLOptions(context)

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    return connection, channel


def publish_message(msg_payload):
    connection = None
    try:
        connection, channel = create_connection()
        msg_payload["timestamp"] = datetime.now().isoformat()

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(msg_payload),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=str(uuid.uuid4()),
                timestamp=int(time.time()),
            ),
        )

        print(f" [x] Sent {msg_payload} to {QUEUE_NAME}")

        return True
    except Exception as e:
        print(f"Error publishing message: {str(e)}")
        return False
    finally:
        if connection and not connection.is_closed:
            connection.close()
