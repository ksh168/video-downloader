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
        retry_count = body_json.get("retry_count", 0)
        
        print(f"Processing message {properties.message_id} with body {body_json},  (attempt {retry_count + 1}/5)")

        # Check retry count BEFORE processing
        if retry_count >= 4:  # Changed from 5 to 4 since we're counting from 0
            print(f"Max retries reached for message {properties.message_id}. Discarding.")
            ch.basic_ack(delivery_tag=method.delivery_tag)
            return

        # Process the message
        download_task = download_file_and_upload_to_s3(body_json.get("url"))

        if not download_task.get("success"):
            # Increment retry count and requeue
            body_json["retry_count"] = retry_count + 1
            ch.basic_publish(
                exchange="",
                routing_key=os.getenv("QUEUE_NAME"),
                body=json.dumps(body_json),
                properties=pika.BasicProperties(
                    delivery_mode=pika.DeliveryMode.Persistent,
                    message_id=properties.message_id
                )
            )
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)
            return

        ch.basic_ack(delivery_tag=method.delivery_tag)
        print(f"Successfully processed message {properties.message_id}")

    except Exception as e:
        print(f"Error processing message: {str(e)}")
        if retry_count < 4:  # Changed from 5 to 4
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=True)
        else:
            ch.basic_nack(delivery_tag=method.delivery_tag, requeue=False)

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
                    # Wait before reconnecting
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
