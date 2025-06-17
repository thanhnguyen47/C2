from flask import Flask, render_template, Response
import logging
import time
import sys
import psutil
import json
import os

app = Flask(__name__)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

MAX_CPU_USAGE = 70
MAX_RAM_USAGE = 150  
MAX_CONNECTIONS = 200
MAX_BYTES_IO = 3000000
WINDOW_SIZE = 10

crashed = False
crash_reason = ""

network_stats = {"bytes_sent": 0, "bytes_recv": 0, "last_update": time.time()}
traffic_data = {
    "timestamps": [],
    "bytes_io": [],
    "cpu_usage": [],
    "ram_usage": [],
    "connections": []
}
last_cpu_usage = 0
last_cpu_time = 0

def get_container_ram_usage():
    try:
        with open('/sys/fs/cgroup/memory/memory.usage_in_bytes', 'r') as f:
            ram_bytes = int(f.read().strip())
        return ram_bytes / (1024 ** 2)
    except Exception as e:
        logging.error(f"Error reading container RAM: {e}")
        return 0

def get_container_cpu_usage():
    global last_cpu_usage, last_cpu_time
    try:
        with open('/sys/fs/cgroup/cpuacct/cpuacct.usage', 'r') as f:
            cpu_time = int(f.read().strip()) / 1_000_000_000
        current_time = time.time()
        if last_cpu_time == 0:
            last_cpu_time = cpu_time
            last_cpu_usage = current_time
            return 0
        time_diff = current_time - last_cpu_usage
        cpu_diff = cpu_time - last_cpu_time
        if time_diff <= 0:
            return 0
        cpu_usage = (cpu_diff / time_diff) * 100
        last_cpu_usage = current_time
        last_cpu_time = cpu_time
        cpu_usage = min(cpu_usage, 100)
        logging.info(f"CPU usage: {cpu_usage:.2f}%")
        return cpu_usage
    except Exception as e:
        logging.error(f"Error reading container CPU: {e}")
        return 0

def get_container_network_io():
    try:
        bytes_sent = int(open('/sys/class/net/eth0/statistics/tx_bytes', 'r').read().strip())
        bytes_recv = int(open('/sys/class/net/eth0/statistics/rx_bytes', 'r').read().strip())
        return bytes_sent, bytes_recv
    except Exception as e:
        logging.error(f"Error reading container Network I/O: {e}")
        return 0, 0

def get_raw_connections():
    """Đếm kết nối thô từ /proc/net/tcp bao gồm SYN_SENT và SYN_RECV"""
    try:
        with open('/proc/net/tcp', 'r') as f:
            lines = f.readlines()
        connections = [line for line in lines[1:] if '0A' in line.split()[3]]  # 0A = SYN_SENT hoặc SYN_RECV
        logging.info(f"Raw connections count: {len(connections)}")
        return len(connections)
    except Exception as e:
        logging.error(f"Error reading raw connections: {e}")
        return 0

def get_container_connections():
    try:
        connections = psutil.net_connections()
        container_pid = os.getpid()
        container_connections = [
            conn for conn in connections
            if conn.pid == container_pid and conn.status in ['LISTEN', 'ESTABLISHED', 'SYN_SENT', 'SYN_RECV']
        ]
        return len(container_connections)
    except Exception as e:
        logging.error(f"Error reading container connections: {e}")
        return 0

def update_network_stats():
    global network_stats, traffic_data
    current_time = time.time()
    time_diff = current_time - network_stats["last_update"]
    if time_diff > 0:
        bytes_sent, bytes_recv = get_container_network_io()
        bytes_sent_diff = bytes_sent - network_stats["bytes_sent"]
        bytes_recv_diff = bytes_recv - network_stats["bytes_recv"]
        bytes_io_speed = (bytes_sent_diff + bytes_recv_diff) / time_diff if time_diff > 0 else 0
        cpu_usage = get_container_cpu_usage()
        ram_usage = get_container_ram_usage()
        connections = get_raw_connections()  # Sử dụng raw connections
        traffic_data["timestamps"].append(current_time)
        traffic_data["bytes_io"].append(bytes_io_speed)
        traffic_data["cpu_usage"].append(cpu_usage)
        traffic_data["ram_usage"].append(ram_usage)
        traffic_data["connections"].append(connections)

        if len(traffic_data["timestamps"]) > 30:
            for key in traffic_data:
                traffic_data[key].pop(0)

        network_stats["bytes_sent"] = bytes_sent
        network_stats["bytes_recv"] = bytes_recv
        network_stats["last_update"] = current_time

    return cpu_usage, ram_usage, connections

def event_stream():
    global crashed, crash_reason
    cpu_history = []
    ram_history = []
    conn_history = []
    io_history = []
    while True:
        cpu_usage, ram_usage, connections = update_network_stats()
        cpu_history.append(cpu_usage)
        ram_history.append(ram_usage)
        conn_history.append(connections)
        io_history.append(sum(traffic_data["bytes_io"][-WINDOW_SIZE:]) / WINDOW_SIZE if traffic_data["bytes_io"] else 0)
        if len(cpu_history) > WINDOW_SIZE:
            cpu_history.pop(0)
            ram_history.pop(0)
            conn_history.pop(0)
            io_history.pop(0)

        cpu_avg = sum(cpu_history) / len(cpu_history) if cpu_history else 0
        ram_avg = sum(ram_history) / len(ram_history) if ram_history else 0
        conn_avg = sum(conn_history) / len(conn_history) if conn_history else 0
        io_avg = sum(io_history) / len(io_history) if io_history else 0

        logging.info(f"Current RAM usage: {ram_usage} MB")
        logging.info(f"CPU average (last {WINDOW_SIZE} samples): {cpu_avg}%")
        logging.info(f"Network I/O average (last {WINDOW_SIZE} samples): {io_avg:.2f} bytes/s")
        if cpu_avg > MAX_CPU_USAGE:
            crashed = True
            crash_reason = 'CPU overload'
            yield f"event: crash\ndata: {json.dumps({'reason': crash_reason})}\n\n"
            break
        elif ram_avg > MAX_RAM_USAGE:
            crashed = True
            crash_reason = 'RAM overload'
            yield f"event: crash\ndata: {json.dumps({'reason': crash_reason})}\n\n"
            break
        elif conn_avg > MAX_CONNECTIONS:
            crashed = True
            crash_reason = 'Too many connections (SYN flood detected)'
            yield f"event: crash\ndata: {json.dumps({'reason': crash_reason})}\n\n"
            break
        elif io_avg > MAX_BYTES_IO:
            crashed = True
            crash_reason = 'Network I/O overload'
            yield f"event: crash\ndata: {json.dumps({'reason': crash_reason})}\n\n"
            break

        timestamps = [time.strftime('%H:%M:%S', time.localtime(t)) for t in traffic_data["timestamps"]]
        data = {
            "timestamps": timestamps,
            "bytes_io": traffic_data["bytes_io"],
            "cpu_usage": traffic_data["cpu_usage"],
            "ram_usage": traffic_data["ram_usage"],
            "connections": traffic_data["connections"]
        }
        yield f"data: {json.dumps(data)}\n\n"
        time.sleep(0.5)

@app.route('/')
def home():
    if crashed:
        timestamps = [time.strftime('%H:%M:%S', time.localtime(t)) for t in traffic_data["timestamps"]]
        return render_template('crashed.html',
                            timestamps=timestamps,
                            bytes_io=traffic_data["bytes_io"],
                            cpu_usage=traffic_data["cpu_usage"],
                            ram_usage=traffic_data["ram_usage"],
                            connections=traffic_data["connections"],
                            crash_reason=crash_reason)
    update_network_stats()
    timestamps = [time.strftime('%H:%M:%S', time.localtime(t)) for t in traffic_data["timestamps"]]
    return render_template('home.html', 
                          timestamps=timestamps,
                          bytes_io=traffic_data["bytes_io"],
                          cpu_usage=traffic_data["cpu_usage"],
                          ram_usage=traffic_data["ram_usage"],
                          connections=traffic_data["connections"])

@app.route('/events')
def events():
    return Response(event_stream(), mimetype='text/event-stream')

@app.errorhandler(Exception)
def handle_exception(e):
    update_network_stats()
    timestamps = [time.strftime('%H:%M:%S', time.localtime(t)) for t in traffic_data["timestamps"]]
    crash_reason = str(e)
    return render_template('crashed.html',
                          timestamps=timestamps,
                          bytes_io=traffic_data["bytes_io"],
                          cpu_usage=traffic_data["cpu_usage"],
                          ram_usage=traffic_data["ram_usage"],
                          connections=traffic_data["connections"],
                          crash_reason=crash_reason), 500

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=80)