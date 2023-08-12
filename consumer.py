from kafka import KafkaConsumer
from json import loads
from time import sleep
from datetime import datetime
from google.cloud.sql.connector import Connector
import os
from datetime import datetime

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "D:\F1ProjectSQL\keys/application_default_credentials.json"
EXTERN_IP = "<EXTERN_IP>"
connection = Connector()

connect = connection.connect(
    instance_connection_string="f1-data-project-388409:europe-west2:f1postgres",
    driver = "pg8000",
    user = "postgres",
    password = "",
    db = "f1"
)

cur = connect.cursor()
consumer = KafkaConsumer(
    'lapdata',
    bootstrap_servers = EXTERN_IP,
    group_id = "test-consumer-group",
    enable_auto_commit = True,
    value_deserializer = lambda x: loads(x.decode('utf-8'))
)

for event in consumer:
    event_data = event.value #capture the event in the log.
    
    time_out_unformat = datetime.now()
    time_out = time_out_unformat.strftime("%H:%M:%S.%f")[:-3]

    val = tuple(str(data) for data in event_data) #stringify all values

    val = val + (str(time_out),)
    string = f"INSERT INTO iracing_data (system_time, track_id, car_id, session_type, lap_number, last_lap_time, current_lap_time, gear, speed, rpm, throttle_pcnt, brake_pcnt, lat_g, long_g, lap_dist, pitch, LF_shock_vel , LR_shock_vel , RF_shock_vel , RR_shock_vel, LF_Temp, LR_Temp, RF_Temp, RR_Temp, time_in, time_out) values {val}"
    print(string)
    cur.execute(string)
    connect.commit()


connect.close()