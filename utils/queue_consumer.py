import pika, pika.exceptions
import os, json
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


# def send_heartbeat(ch):
#     while True:
#         # Use a dummy delivery tag for heartbeat
#         ch.basic_nack(delivery_tag=0)  # Send a heartbeat
#         print(" [x] Sent heartbeat to RabbitMQ")
#         time.sleep(30)  # Send every 30 seconds


# Function to send heartbeats in a separate thread
def send_heartbeat(connection):
    while True:
        try:
            # Make sure the connection is still open
            if connection.is_open:
                connection.process_data_events()  # Send a heartbeat frame to RabbitMQ
            else:
                print("Connection is closed, exiting heartbeat thread.")
                break
            time.sleep(
                int(os.getenv("HEARTBEAT_INTERVAL"))
            )  # Sleep for the heartbeat interval
        except Exception as e:
            print(f"Error in heartbeat thread: {e}")
            break


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

                raise Exception(e)
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


def create_connection():
    """Create a new connection and channel"""
    params = pika.URLParameters(CLOUDAMQP_URL)
    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=QUEUE_NAME, durable=True)
    return connection, channel


def start_consumer():
    while True:
        try:
            global connection, channel
            connection, channel = create_connection()
            
            # Start heartbeat thread before consuming messages
            heartbeat_thread = threading.Thread(
                target=send_heartbeat, 
                args=(connection,)
            )
            heartbeat_thread.daemon = True
            heartbeat_thread.start()
            
            channel.basic_qos(prefetch_count=1)
            channel.basic_consume(queue=QUEUE_NAME, on_message_callback=callback)

            print(" [*] Waiting for messages. To exit press CTRL+C")
            channel.start_consuming()
            
        except pika.exceptions.ConnectionClosed as e:
            print(f"Connection closed: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
            continue
        except pika.exceptions.ChannelClosed as e:
            print(f"Channel closed: {e}. Reconnecting in 5 seconds...")
            time.sleep(5)
            continue
        except Exception as e:
            print(f"Error: {e} while consuming messages from {QUEUE_NAME}")
            time.sleep(5)
            continue
        finally:
            try:
                if connection and connection.is_open:
                    connection.close()
            except Exception as e:
                print(f"Error closing connection: {e}")
                pass


def consume_messages():
    # Create and start a daemon thread for the consumer
    consumer_thread = threading.Thread(target=start_consumer)
    consumer_thread.daemon = True
    consumer_thread.start()
