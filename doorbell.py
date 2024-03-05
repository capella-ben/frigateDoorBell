import json
import requests
import io
import configparser
from PIL import Image
import paho.mqtt.client as mqtt
from windows_toasts import Toast, ToastDisplayImage, InteractableWindowsToaster, ToastDuration, AudioSource, ToastAudio

# https://windows-toasts.readthedocs.io/en/latest/getting_started.html

config = configparser.ConfigParser()
config.read('doorbell.ini')

# MQTT settings
mqtt_broker = config['MQTT']['mqtt broker']
mqtt_port = config.getint('MQTT', 'mqtt port')
mqtt_topic = config['MQTT']['mqtt topic']
mqtt_username = config['MQTT']['mqtt username']
mqtt_password = config['MQTT']['mqtt password']

# Camera settings
targetCamera = config['Camera']['target camera']
targetZone = config['Camera']['target zone']

# Frigate API settings
frigate_api_base_url = config['Frigate']['frigate api base url']

# Frigate will spit out a stream of events.  We are only interested in the first one, so we need to track the event ID.
previousId = ""

def on_message(client, userdata, msg):
    global previousId
    try:
        # Decode the JSON message
        payload = json.loads(msg.payload.decode("utf-8"))
        print(json.dumps(payload, indent=2))
        print()
        
        # Extract the ID from the JSON
        event_id = payload['before'].get("id")
        camera = payload['before'].get('camera')
        
        print(f"Found event: {event_id} for camera: {camera}")

        if event_id and event_id != previousId and camera == targetCamera:
            if targetZone != '' and (targetZone in payload['before']['current_zones'] or targetZone in payload['after']['current_zones']):
                previousId = event_id
                # Make HTTP GET request to retrieve snapshot
                snapshot_url = f"{frigate_api_base_url}/api/events/{event_id}/snapshot.jpg"
                response = requests.get(snapshot_url)

                if response.status_code == 200:
                    print(f"Snapshot received for event ID {event_id}")

                    # Save teh image to file
                    image = Image.open(io.BytesIO(response.content))
                    temp_image_path = "thumbnail.jpg"
                    image.save(temp_image_path)

                    # Notify!
                    toaster = InteractableWindowsToaster('Front_Door_Bell')
                    newToast = Toast()
                    newToast.text_fields = ['Someone is at the front door!']
                    newToast.AddImage(ToastDisplayImage.fromPath('thumbnail.jpg'))
                    newToast.duration = ToastDuration.Long
                    newToast.audio = ToastAudio(AudioSource.Alarm, looping=True)
                    toaster.show_toast(newToast)

                else:
                    print(f"Failed to retrieve snapshot for event ID {event_id}. Status Code: {response.status_code}")
            
    except Exception as e:
        print(f"Error processing message: {e}")





# Initialize MQTT client
client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_message = on_message
client.username_pw_set(mqtt_username, mqtt_password)

# Connect to MQTT broker
client.connect(mqtt_broker, mqtt_port, 60)
client.subscribe(mqtt_topic)

print("Subscribed. Monitoring...")
# Loop to handle incoming messages
client.loop_forever()



