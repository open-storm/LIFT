# Python stuff
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from scipy import integrate
import pandas as pd
import datetime
# SWMM toolkits
import swmmAPI_v2 as sm
import swmmtoolbox.swmmtoolbox as sb
# Set up client
import influxdb
import requests

## Influx cloud
username = "username"
password = "password"
port = 8086
db = "db"
host = "HOST_URL"

# Setup the client
client = influxdb.InfluxDBClient(host=host,
                port=port,
                username=username,
                password=password,
                database=db)

def convert_timestamps(series):
    time = [i // 10**9 for i in series.index.astype(np.int64)]
    return time

def generate_data(time, series, tags):
    temp_str = tags["measure"]+",Name="+tags["name"]+",Type="+tags["type"]+",Group="+str(tags["group"])+",Location="+tags["location"]+",taga=un"+" value="
    data = [temp_str+str(i[0])+" "+str(j)+"000000000" for i,j in zip(series.values, time)]
    return data

def to_influx(client, data):
    client.write_points(data, protocol="line")

def outflux(client, outfile, control_locations):
    # Pick a point from the points of interest
    for tag in control_locations.to_dict(orient='records'):
        # Generate the series from the output file
        series = sb.extract(outfile, sm.make_extract_string(tag["name"],tag["type"],tag["measure"]))
        # make time to unix
        time = convert_timestamps(series)
        # make the line
        data = generate_data(time, series, tag)
        # write to influx!
        to_influx(client, data)

def outflux_1(client, outfile, control_locations):
    # Pick a point from the points of interest
    for tag in control_locations.to_dict(orient='records'):
        # Generate the series from the output file
        series = sb.extract(outfile, sm.make_extract_string(tag["name"],tag["type"],tag["measure"]))
        # make time to unix
        time = convert_timestamps(series)
        # make the line
        data = generate_data(time, series, tag)
        # write to influx!
        data = '\n'.join(data)
        u = "username"
        p = "password"
        port = 8086
        db = "db"
        host = "your_url"
        post_header = {
	'Host': '%s:%s'%(host,port),
	'Connection': 'close',
	'Content-Length': '%d'%len(data),
	'Content-Type': 'plain/text'}

        r = requests.post('http://%s:%s/write?db=%s&u=%s&p=%s'%(host,port,db,u,p),headers = post_header,data = data)
        print(r.status_code)

### TEST
outfile = "./Lift_1/OUTPUT_FILE.out"
outflux_1(client, outfile, pd.read_csv("./Lift_1/POINTS_OF_INTEREST.csv"))
