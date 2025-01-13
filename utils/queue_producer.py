#!/usr/bin/env python
import pika, os, json, uuid, time
from datetime import datetime

# Get the CloudAMQP URL from environment variable
CLOUDAMQP_URL = os.getenv("CLOUDAMQP_URL")

# Parse the AMQP URL
params = pika.URLParameters(CLOUDAMQP_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()

QUEUE_NAME = os.getenv("QUEUE_NAME")
channel.queue_declare(queue=QUEUE_NAME, durable=True)


def publish_message(msg_payload):
    try:
        msg_payload["timestamp"] = datetime.now().isoformat()

        channel.basic_publish(
            exchange="",
            routing_key=QUEUE_NAME,
            body=json.dumps(msg_payload),
            properties=pika.BasicProperties(
                delivery_mode=pika.DeliveryMode.Persistent,
                message_id=str(uuid.uuid4()),
                timestamp=int(time.time())
            )
        )
        print(f" [x] Sent {msg_payload} to {QUEUE_NAME}")

    except Exception as e:
        print(f"Error: {e} \nShutting down producer for {QUEUE_NAME}...")
    # finally:
    #     connection.close()
