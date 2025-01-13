import pika, os, json
import threading
from utils.download_and_upload import download_file_and_upload_to_s3
import time

# Get the CloudAMQP URL from environment variable
CLOUDAMQP_URL = os.getenv("CLOUDAMQP_URL")

# Parse the AMQP URL
params = pika.URLParameters(CLOUDAMQP_URL)
connection = pika.BlockingConnection(params)
channel = connection.channel()

QUEUE_NAME = os.getenv("QUEUE_NAME")
channel.queue_declare(queue=QUEUE_NAME, durable=True)


def send_heartbeat(ch):
    while True:
        ch.basic_ack(delivery_tag=None)  # Send a heartbeat
        print(" [x] Sent heartbeat to RabbitMQ")
        time.sleep(30)  # Send every 30 seconds


def callback(ch, method, properties, body):
    try:
        body_json = json.loads(body)
        print(
            f"Received message with message_id: {properties.message_id} with body_json: {body_json} from QUEUE_NAME: {QUEUE_NAME} with retry_count: {body_json.get('retry_count', 0)}"
        )

        # Check retry count
        retry_count = body_json.get("retry_count", 0)
        if retry_count >= 5:
            print(
                f"Max retries reached for message {properties.message_id} in the queue {QUEUE_NAME}. Discarding message."
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Start heartbeat thread
        heartbeat_thread = threading.Thread(target=send_heartbeat, args=(ch,))
        heartbeat_thread.daemon = True
        heartbeat_thread.start()

        # Perform the long task
        download_task = download_file_and_upload_to_s3(body_json.get("url"))

        if not download_task.get("success"):
            raise Exception(download_task.get("error"))

        print(
            f" [x] Done processing with message_id: {properties.message_id} for QUEUE_NAME: {QUEUE_NAME}"
        )
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"Error processing message {properties.message_id}: {e}")

        # Update retry count
        body_json["retry_count"] = body_json.get("retry_count", 0) + 1

        if body_json["retry_count"] < 5 and not body_json.get("is_success"):
            # Requeue with updated retry count using the existing publish function
            try:
                channel.basic_publish(
                    exchange="",
                    routing_key=QUEUE_NAME,
                    body=json.dumps(body_json),
                    properties=pika.BasicProperties(
                        message_id=properties.message_id,
                        delivery_mode=pika.DeliveryMode.Persistent,
                        timestamp=int(time.time()),
                    ),
                )

                print(
                    f" [x] Message with message_id: {properties.message_id} of QUEUE_NAME: {QUEUE_NAME} requeued (retry count: {body_json['retry_count']})"
                )
            except Exception as e:
                print(
                    f" [x] Failed to requeue message with message_id: {properties.message_id}"
                )
        elif body_json.get("is_success"):
            print(
                f" [x] Message with message_id: {properties.message_id} of QUEUE_NAME: {QUEUE_NAME} is successful. Discarding message."
            )
        else:
            print(
                f" [x] Max retries reached for message with message_id: {properties.message_id}. Discarding message."
            )

        # Acknowledge the original message
        ch.basic_ack(delivery_tag=method.delivery_tag)


def start_consumer():
    try:
        channel.basic_qos(prefetch_count=1)
        channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

        print(" [*] Waiting for messages. To exit press CTRL+C")
        channel.start_consuming()
    except Exception as e:
        print(f"Error: {e} while consuming messages from {QUEUE_NAME}")


def consume_messages():
    # Create and start a daemon thread for the consumer
    consumer_thread = threading.Thread(target=start_consumer)
    consumer_thread.daemon = (
        True  # This ensures the thread will exit when the main program exits
    )
    consumer_thread.start()
