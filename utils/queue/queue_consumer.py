import pika
import os
import json
import threading
import time
from utils.s3.download_and_upload import download_file_and_upload_to_s3

def create_connection():
    """Create a new connection with automatic connection recovery"""
    params = pika.URLParameters(os.getenv("CLOUDAMQP_URL"))
    # Set heartbeat interval to 580 seconds
    params.heartbeat = int(os.getenv("HEARTBEAT_INTERVAL"))
    # Enable automatic recovery
    params.connection_attempts = 3
    params.retry_delay = 5

    connection = pika.BlockingConnection(params)
    channel = connection.channel()
    channel.queue_declare(queue=os.getenv("QUEUE_NAME"), durable=True)
    return connection, channel

def process_message(ch, method, properties, body):
    try:
        body_json = json.loads(body)
        url = body_json.get("url")
        
        print(f"Processing message {properties.message_id} with URL {url}")

        # Process the message
        download_task = download_file_and_upload_to_s3(url)

        if download_task.get("success"):
            ch.basic_ack(delivery_tag=method.delivery_tag)
        else:
            # If download failed, reject the message and requeue
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

    except Exception as e:
        print(f"Error processing message: {str(e)}")
        ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)

def consume_messages():
    def start_consumer():
        while True:
            try:
                connection, channel = create_connection()
                
                # Set QoS prefetch to 1 to ensure fair dispatch
                channel.basic_qos(prefetch_count=1)
                
                # Generate a unique consumer tag
                consumer_tag = f"consumer_{os.getenv('RENDER_SERVICE_NAME', 'default')}_{os.getpid()}"
                print(f" [*] Connected to RabbitMQ, waiting for messages as {consumer_tag}...")
                
                # Start consuming messages with the unique consumer tag
                channel.basic_consume(
                    queue=os.getenv("QUEUE_NAME"),
                    on_message_callback=process_message,
                    consumer_tag=consumer_tag
                )
                
                try:
                    channel.start_consuming()
                except KeyboardInterrupt:
                    channel.stop_consuming()
                    break
                except Exception as e:
                    print(f"Consumer error: {str(e)}")
                    time.sleep(5)
                finally:
                    try:
                        if connection and not connection.is_closed:
                            connection.close()
                    except Exception:
                        pass

            except Exception as e:
                print(f"Connection error: {str(e)}")
                time.sleep(5)  # Wait before reconnecting

    # Start consumer in a separate thread
    consumer_thread = threading.Thread(target=start_consumer, daemon=True)
    consumer_thread.start()
