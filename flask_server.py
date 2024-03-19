from flask import Flask, request, jsonify
from os import listdir
from os.path import isfile, join
from threading import Thread
import time

"""
Format:

/api/sessions

/api/session_start/<id>
/api/session_end/<id>
/api/session_csv/<id>

/api/gps/<id>/<timestamp>&<lat>&<long>
/api/step_count/<id>/<timestamp>&<lat>&<long>

/api/gps/<id>?ts=<timestamp>&lat=<latitude>&long=<longitude>
"""

CSV_PATH = "./data/"

class TrainingSession:
    def __init__(self, id):
        self.in_progress = True
        self.id = id
        self.gps_data = []
        self.step_count_data = []
        self.save_file = CSV_PATH + id + ".csv"
        self.modified = False
        self.keep_saving = True
        self.save_delay = 1
        self.save_task = Thread(target = self._save_loop)
        self.save_task.start()

    def end_session(self):
        self.in_progress = False
        self.keep_saving = False
        self.save_task.join()

    def add_gps(self, ts, lat, long):
        self.gps_data.append((ts, lat, long))
        self.modified = True
    
    def add_step_count(self, ts, step_count):
        self.step_count_data.append((ts, step_count))
        self.modified = True

    def _save_loop(self):
        while self.keep_saving:
            time.sleep(self.save_delay)
            
            if not self.modified:
                continue

            print("Saving...")
            data = [(ts, lat, long, None) for ts,lat,long in self.gps_data]
            data.extend([(ts, None, None, step_count) for ts,step_count in self.step_count_data])
            self.modified = False
            
            data = sorted(data, key = lambda x: float(x[0]))
            # data_str = '\n'.join(','.join(str(x) if x != None else "" for x in data))
            data_str = '\n'.join(','.join(str(y) if y != None else "" for y in x) for x in data)

            with open(self.save_file, "w") as f:
                f.write(data_str)

class TrainingSessionHandler:
    def __init__(self):
        self.sessions = dict()

    def start_session(self, id):
        self.sessions[id] = TrainingSession(id)
    
    def end_session(self, id):
        self.sessions[id].end_session()

    def add_gps(self, id, ts, lat, long):
        self.sessions[id].add_gps(ts, lat, long)

    def add_step_count(self, id, ts, step_count):
        self.sessions[id].add_step_count(ts, step_count)

app = Flask(__name__)
session_handler = TrainingSessionHandler()

def get_files(directory):
    return [f for f in listdir(directory) if isfile(join(directory, f))]

def get_session_data(session_name):
    with open(CSV_PATH + session_name, "r") as f:
        return f.read()

def get_session_names():
    return get_files(CSV_PATH)

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    return jsonify(get_session_names())

@app.route('/api/session_start/<id>', methods=['POST'])
def start_session(id):
    session_handler.start_session(id)
    return f"Started session {id}"

@app.route('/api/session_end/<id>', methods=['POST'])
def end_session(id):
    session_handler.end_session(id)
    return f"Ended session {id}"

@app.route('/api/session_csv/<id>', methods=['GET'])
def get_session_csv(id):
    try:
        sessions = get_session_names()
        if id in sessions:
            return get_session_data(id)
        else:
            return f"Error 100, could not find session with {id}"
    except:
        return f"Error 101, could not find session with {id}"

@app.route('/api/gps/<id>', methods=['POST'])
def post_gps_data(id):
    lat = request.args.get('lat')
    long = request.args.get('long')
    timestamp = request.args.get('ts')
    session_handler.add_gps(id, timestamp, lat, long)
    return f"GPS Data Received: ID={id}, Timestamp={timestamp}, Lat={lat}, Long={long}"

@app.route('/api/step_count/<id>', methods=['POST'])
def post_step_count(id):
    step_count = request.args.get('count')
    timestamp = request.args.get('ts')
    session_handler.add_step_count(id, timestamp, step_count)
    return f"Step Count Data Received: ID={id}, Timestamp={timestamp}, Step Count={step_count}"

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8000, debug=True)
