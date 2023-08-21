# The following file is adapted from Mihail Latyshov's pyiRSDK documentation available at: https://github.com/kutu/pyirsdk/blob/master/tutorials/03%20Base%20application.md

import irsdk
import time
from datetime import datetime
from kafka import KafkaProducer
from json import dumps
from google.cloud.sql.connector import Connector
import os

os.environ['GOOGLE_APPLICATION_CREDENTIALS']= "D:\F1ProjectSQL\keys/application_default_credentials.json"
EXTERN_IP = '<EXTERN_IP>'
iR_isRunning = False

# Configuration variables

start_lap = 1
laps_to_log = 1
end_lap = start_lap + laps_to_log

# PostgreSQL connection

connection = Connector()

connect = connection.connect(
    instance_connection_string="f1-data-project-388409:europe-west2:f1postgres",
    driver = "pg8000",
    user = "postgres",
    password = "", # password left blank for security reasons.
    db = "f1"
)

cursor = connect.cursor()

#Initialise class members to initial values

class State: #Class to store status of the simulator
    ir_connected = False
    sys_time = 0

class CarStatus: #Class representing car on track
    rpm = 0
    time = 0
    fuel_level = 0
    speed = 0
    throttle_pos = 0
    brake_pos = 0
    lat_g = 0
    long_g = 0
    last_lap_time = 0
    lap_pct = 0
    gear = 0

    lap_dist = 0

    LF_shock_vel = 0
    LR_shock_vel = 0
    RF_shock_vel = 0
    RR_shock_vel = 0

    pitch = 0

    LFTemp = 0
    LRTemp = 0
    RFTemp = 0
    RRTemp = 0

class SessionStatus: #Class to store track data.
    track_id = ""
    car_id = ""
    track_temp = 0
    lap_num = 0
    session_type = ""
    sector_1_percent = 0
    sector_2_percent = 0
    sector_3_percent = 0

# Kafka producer setup.

producer = KafkaProducer(
    bootstrap_servers = EXTERN_IP + ":9091", # Change EXTERN_IP to the IP of your Kafka server.
    value_serializer = lambda x: dumps(x).encode('utf-8'),
    api_version = (2,5,0)
)

def is_iracing_connected(state, ir):
    if state.ir_connected and not (ir.is_initialized and ir.is_connected):
        state.ir_connected = False

        ir.shutdown()
        print("iRSDK Disconnected")
        return False

    elif not state.ir_connected and ir.startup() and ir.is_initialized and ir.is_connected:
        state.ir_connected = True
        print("iRSDK Connected")
        return True

def get_data(ir, Car, Session, logging, timestamp): #Function to pull data to be passed to kafka
    ir.freeze_var_buffer_latest() #Freezes the variables in the buffer to ensure consistency of data across ticks.

    #Car Information
    if "RPM" in logging:
        print("E")
        Car.rpm = ir['RPM'] # Car Engine Speed in revolutions per minute.
    if "Gear" in logging:
        Car.gear = ir['Gear'] # Current selected gear, -1 = Reverse, 0 = Neutral, etc.
    if "Current Lap Time" in logging:
        Car.time = ir['LapCurrentLapTime'] # Current lap time in decimal minutes, e.g.: 1.42 minutes or 85.2 seconds.
        if Car.time == None:
            Car.time = 0.0 # Estimation of current laptime as shown in F3 BB
        Car.lap_pct = ir['LapDistPct']
    if "Fuel Level" in logging:
        Car.fuel_level = ir['FuelLevel'] # Car fuel level in Litres
                                         # This value updates on the S/F line
                                         # every lap, and is not live data. See documentation for more info.
    if "Speed" in logging:
        Car.speed = ir['Speed'] * 3.6 #Car GPS velocity in kph
    if "Throttle" in logging:
        Car.throttle_pos = ir['Throttle'] * 100 #Throttle position percentage
    if "Brake" in logging:
        Car.brake_pos = ir['Brake'] * 100 #Brake position percentage
    if "Lateral G" in logging:
        Car.lat_g = ir['LatAccel'] / 9.81 #Lateral Acceleration including gravity in units of 'g'
    if "Longitudinal G" in logging:
        Car.long_g = ir['LongAccel'] / 9.81 #Longitudinal Acceleration including gravity in units of 'g'
    if "Last Lap Time" in logging:
        Car.last_lap_time = ir['LapLastpLapTime'] # Last lap time in minutes and decimal minutes e.g.: 1.42 min
        if Car.last_lap_time == None:
            Car.last_lap_time = 0.0

    #Session Information
    
    Session.track_id = ir['WeekendInfo']['TrackDisplayName'] #Shortened track name, e.g.: "Indianapolis Road Course".
    Session.car_id = ir['DriverInfo']['Drivers'][0]['CarScreenNameShort'] #Shortened Car Name in readable English, .e.g.: "Dallara P217 LMP2".

    if "Track Temp" in logging:
        Session.track_temp = ir['WeekendInfo']['TrackAirTemp'] # Track Surface Temperature in celsius
    if "Lap Number" in logging:
        Session.lap_num = ir['Lap'] #Current lap number
    if "Session Type" in logging:
        Session.session_type = ir['SessionInfo']['Sessions'][0]['SessionType'] # Current session type, e.g.: "Offline Testing"
        if Session.session_type == None:
            Session.session_type = "NULL"

    #System time and formatting
    State.sys_time = datetime.now() # Current time
    State.sys_time = State.sys_time.strftime("%H:%M:%S.%f")[:-3] # Current time formatted to HH:MM:SS.mmm

    Car.lap_dist = ir['LapDist'] # Current distance of the lap covered in m
    Car.LF_shock_vel = ir['LFshockVel'] # Suspension shock velocities for each corner, unclear which units,
    Car.LR_shock_vel = ir['LRshockVel'] # most likely mm/s as this is a common unit.
    Car.RF_shock_vel = ir['RFshockVel']
    Car.RR_shock_vel = ir['RRshockVel']

    Car.pitch = ir['Pitch'] # Pitch of the car in degrees.

    Car.LFTemp = ir['LFtempCM'] # Due to iRacing's implementation of tyre temp updates
    Car.LRTemp = ir['LRtempCM'] # These values only update either on S/F line, or at
    Car.RFTemp = ir['RFtempCM'] # every pit stop, and are not live. These temps are
    Car.RRTemp = ir['RRtempCM'] # taken from the middle third of the tyre carcass.

    #Kafka logic
    #Format as below:
    
    message = []

    message.append(State.sys_time)

    message.append(Session.track_id)
    message.append(Session.car_id)
    message.append(Session.session_type)
    message.append(Session.lap_num)

    message.append(Car.last_lap_time)
    message.append(Car.time)
    message.append(Car.gear)
    message.append(Car.speed)
    message.append(Car.rpm)
    message.append(Car.throttle_pos)
    message.append(Car.brake_pos)
    message.append(Car.lat_g)
    message.append(Car.long_g)
    message.append(Car.lap_dist)
    message.append(Car.LF_shock_vel)
    message.append(Car.LR_shock_vel)
    message.append(Car.RF_shock_vel)
    message.append(Car.RR_shock_vel)
    #message.append(timestamp)

    message.append(Car.pitch)
    message.append(Car.LFTemp)
    message.append(Car.LRTemp)
    message.append(Car.RFTemp)
    message.append(Car.RRTemp)
    message.append(State.sys_time)
    
    producer.send('lapdata', value = message)
    producer.flush()
    
    
def init_iR(check_list):
    print(f"Logging selected: {check_list}")
    ir = irsdk.IRSDK()
    state = State()
    Car = CarStatus()
    Session = SessionStatus()

    timestamp = datetime.now() # current system time.
    timestamp = timestamp.strftime("%Y_%m_%d_%H_%M_%S") # replace 'iracing_data' with 'timestamp_SessionStatus.Car_id' for compartmentalisation.
    cursor.execute(f"create table if not exists iracing_data (id serial, system_time time without time zone, track_id text, car_id text, session_type text, lap_number int, last_lap_time real, current_lap_time real, gear int, speed real, rpm real, throttle_pcnt real, brake_pcnt real, lat_g real, long_g real, lap_dist real, LF_shock_vel real, LR_shock_vel real, RF_shock_vel real, RR_shock_vel real, pitch real, LF_Temp real, LR_Temp real, RF_Temp real, RR_Temp real, time_in time without time zone, time_out time without time zone, primary key (id, system_time, track_id, car_id));")
    connect.commit() # executes the f-string statement in SQL.

    try: #Test for open connection and loop.
        while True:
            is_iracing_connected(state, ir) #Get session status
            if state.ir_connected == True:

                if ir['OnPitRoad'] == False and ir['IsOnTrack'] == True and ir['Lap'] in range(start_lap, end_lap): # IsOnTrack flag guards against collection whilst in garage.
                    # OnPitRoad flag protects against logging data whilst the car is in the pits, as this is largely useless in cars with PSL (Pit Speed Limiter).
                    
                    get_data(ir, Car, Session, check_list, timestamp) # if iracing is connected and car is off pit road, pull data. 
                elif ir['Lap'] == 0 or ir['Lap'] > end_lap:
                    print(f"Please start lap {start_lap} to start logging data for {laps_to_log} lap(s). Waiting...")
                    time.sleep(0.5) # Guards against logging data on the outlap and inlap.
                else:
                    print("Player is not in car, or car is on pit road, waiting...")
                    time.sleep(2) # if car is in garage or driver is in pit-road traversal, do not log.
            else:
                print(" iRacing Not connected, closing...")
                time.sleep(1)
                quit() # if iracing is not connected, kill script and exit.
            time.sleep(1/60) #Interval at which to poll the sim.
    except KeyboardInterrupt :
        pass #If Ctrl+C, then exit. Failsafe.

# The below is largely unneeded, as all execution is done through the UI, but if needed the file can be run
# Direct from Python with all logging enabled.

if "__name__" == "__main__":    


    ir = irsdk.IRSDK()
    state = State()
    Car = CarStatus()
    Session = SessionStatus()


    try: #Test for open connection and loop.
        while True:
            is_iracing_connected() #Get session status
            if state.ir_connected == True:
                get_data() # if iracing is connected, pull data
            else:
                quit()
            time.sleep(1/60) #Interval at which to poll the sim.
    except KeyboardInterrupt:
        pass #If Ctrl+C, then exit.

