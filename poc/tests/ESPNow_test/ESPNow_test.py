import csv
import serial
import time
import statistics
from datetime import datetime
from pathlib import Path

# ==========================================
# CONFIGURATION
# ==========================================
SERIAL_PORT = 'COM11'  # Update this to match your Master ESP32 port (e.g., /dev/ttyUSB0)
BAUD_RATE = 115200
PING_COUNT = 1000     # Number of packets to send


def main():
    try:
        # Open serial connection
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        print(f"Connected to {SERIAL_PORT}. Waiting 2 seconds for boot...")
        time.sleep(2) 
        
        # Clear any startup serial noise
        ser.reset_input_buffer() 
        
        rtt_list = []
        results = []
        
        print(f"Starting {PING_COUNT} pings...")
        for i in range(PING_COUNT):
            # Command the ESP32 to send a ping
            ser.write(b'P')
            
            # Read the response (RTT in microseconds)
            line = ser.readline().decode('utf-8').strip()
            
            if line.isdigit():
                rtt = int(line)
                rtt_list.append(rtt)
                results.append({
                    "ping": i + 1,
                    "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                    "status": "success",
                    "rtt_us": rtt,
                    "one_way_estimate_us": rtt / 2,
                })
                # print(f"Ping {i+1}: RTT = {rtt} us") # Uncomment to see every ping
            else:
                results.append({
                    "ping": i + 1,
                    "timestamp": datetime.now().isoformat(timespec="milliseconds"),
                    "status": "timeout_or_error",
                    "rtt_us": "",
                    "one_way_estimate_us": "",
                })
                print(f"Ping {i+1}: Timeout or Error")
            
            # 10ms delay between pings to prevent network flooding
            time.sleep(0.01) 
            
        ser.close()

        results_dir = Path(__file__).resolve().parents[3] / "test_results"
        results_dir.mkdir(exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        csv_path = results_dir / f"espnow_latency_test_{timestamp}.csv"
        with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=["ping", "timestamp", "status", "rtt_us", "one_way_estimate_us"],
            )
            writer.writeheader()
            writer.writerows(results)

        print(f"Saved raw measurements: {csv_path}")
        
        # Calculate statistics
        if rtt_list:
            median_rtt = statistics.median(rtt_list)
            mean_rtt = statistics.mean(rtt_list)
            
            # One-way latency is half of the Round-Trip Time
            median_one_way = median_rtt / 2
            mean_one_way = mean_rtt / 2
            
            print("\n" + "="*30)
            print("LATENCY RESULTS")
            print("="*30)
            print(f"Successful Pings: {len(rtt_list)} / {PING_COUNT}")
            print(f"Median RTT:       {median_rtt:.2f} us")
            print(f"Mean RTT:         {mean_rtt:.2f} us")
            print("-" * 30)
            print(f"YOUR ONE-WAY CONSTANT (Median): {median_one_way:.0f} us")
            print("="*30)
            
    except serial.SerialException as e:
        print(f"Serial Error: {e}. Is the port correct and not busy?")
    except Exception as e:
        print(f"Unexpected Error: {e}")

if __name__ == '__main__':
    main()