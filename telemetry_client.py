import sys
import re
import traceback
import paramiko
from websocket import create_connection
from time import sleep

HOSTNAME = "192.168.1.1"
USERNAME = "deepracer"
PASSWORD = "deepracer"
SERVER_URL = "ws://localhost:8000/ws/0"

def websocket_connect():
    while True:
        try:
            websocket = create_connection(SERVER_URL, timeout=0.1)
            print("Websocket connected")
            return websocket
        except Exception as e:
            print("Failed to open websocket: %s" % e)
        sleep(1)


ws = websocket_connect()

try:
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(HOSTNAME, 22, USERNAME, PASSWORD)

    print("connected")

    # Check version
    p = re.compile('VERSION_ID="(\d+\.\d+)"')
    stdin, stdout, stderr = client.exec_command("cat /etc/os-release")
    stdin.close()
    for line in iter(lambda: stdout.readline(2048), ""):
        if "VERSION_ID" in line:
            match = p.match(line)
            version = match.group(1)

    print("Version: %s" % version)

    if version == "20.04":
        ros_command = "source /opt/ros/foxy/setup.bash; ros2 topic echo /rosout"
    else:
        # 16.04
        ros_command = "source /opt/ros/kinetic/setup.bash; rostopic echo /rosout_agg"

    p = re.compile('msg: "Setting throttle to (\d+\.\d+)"')
    stdin, stdout, stderr = client.exec_command(ros_command)
    stdin.close()
    for line in iter(lambda: stdout.readline(2048), ""):
        print(line, end="")
        if "Setting throttle to" in line:
            match = p.match(line)
            throttle_raw = float(match.group(1))
            throttle = round(throttle_raw * 100)
            print(throttle)
            try:
                ws.send(str(throttle))
            except Exception as e:
                print("Failed to send to websocket: %s" % e)
                ws = websocket_connect()
                ws.send(str(throttle))


except Exception as e:
    print("*** Caught exception: " + str(e.__class__) + ": " + str(e))
    traceback.print_exc()
    try:
        client.close()
    except:
        pass
    sys.exit(1)
