import os
import paho.mqtt.client as mqtt
from google.cloud import pubsub_v1

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "smart-bin-project-483011-4eaae0f99610.json"
project_id = "smart-bin-project-483011"
topic_id = "smartbin-readings"

publisher = pubsub_v1.PublisherClient()
topic_path = publisher.topic_path(project_id, topic_id)

def on_message(client, userdata, msg):
    payload = msg.payload.decode("utf-8")
    print(f"Received: {payload}")
    publisher.publish(topic_path, payload.encode("utf-8"))
    print("Forwarded to Pub/Sub")

client = mqtt.Client()
client.on_connect = lambda c,u,f,rc: c.subscribe("smartbin/+/data")
client.on_message = on_message
client.connect("localhost", 1883, 60)
client.loop_forever()
