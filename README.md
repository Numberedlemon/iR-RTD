# iR-RTD - Real Time Telemetry Visualisation for iRacing

iR-RTD is a Real Time Telemetry Visualisation tool for iRacing, which was developed for a Master's project for an MSc in Data Science and Engineering at the University of Dundee.

iR-RTD makes use of Apache Kafka and PostgreSQL in the cloud, as well as PowerBI desktop.

# Installation

To install iR-RTD, either clone or download the files from this repository to your local machine, and run:

`pip install -r requirements.txt`

- Install NPGSQL
- Install Microsoft ODBC
- Set up Google Cloud Platforms "Google Application Default Credentials"
- Install PowerBI and disable "encrypt connections"
- Ensure iRacing is fully up to date

## Configuration

Configuration of iR-RTD is can be done by editing `consumer.py` and `RealTimeData.py`. To ensure iR-RTD can run properly,

- Change `EXTERN_IP` and the path to your Google Application Default Credentials file in both `consumer.py` and `RealTimeData.py`.
- Change the `instance_connection_string` in both files to the instance connection string of a PostgreSQL cloud database.

# Running iR-RTD

To run iR-RTD, first start both Kafka and PostgreSQL cloud-based services.

- Run `python consumer.py` to start the consumer.
- Run `python UserInterface.py` to start the UI.
- Start an iRacing Instance.
- Select desired logging parameters, and click start.

