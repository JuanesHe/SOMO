# Kywo Production Firmware - ESP32-C6

Production firmware for distributed ESP32 control system with ESP-NOW clock synchronization.

## Hardware Configuration

### Target Board
- **ESP32-C6-DevKitC-1**
- **Framework**: Arduino
- **Firmware Version**: 3.0.0-Production

### Pin Assignment (Fixed)

| Output | GPIO Pin | Type | Description |
|--------|----------|------|-------------|
| Digital Output 1 | GPIO 5 | Digital | Binary output (HIGH/LOW) |
| Digital Output 2 | GPIO 23 | Digital | Binary output (HIGH/LOW) |
| Digital Output 3 | GPIO 22 | Digital | Binary output (HIGH/LOW) |
| PWM Output | GPIO 4 | PWM | Variable duty cycle (0-255) |
| Static HIGH | GPIO 7 | Digital | Always HIGH after boot |
| Static LOW | GPIO 21 | Digital | Always LOW after boot |

**PWM Specifications:**
- Frequency: 5 kHz
- Resolution: 8-bit (0-255)
- LEDC channel: Allocated automatically by Arduino-ESP32

## System Architecture

### Communication Layers

1. **HTTP/TCP Configuration Layer**
   - **Purpose**: Configuration polling from server
   - **Interval**: 1000ms
   - **Endpoint**: `GET /devices/{device_id}/config`
   - **Payload**: Sequence configuration + master role assignment

2. **ESP-NOW Synchronization Layer**
   - **Purpose**: Microsecond-precision clock synchronization
  - **Interval**: 500ms broadcast (master only)
  - **Latency Compensation**: Calibrated one-way estimate (625us)
  - **Filtering**: Rejects offset changes above 500us; applies 25% of accepted corrections
   - **Target Drift**: <50µs mean

### Execution Model

- **FreeRTOS Architecture**: Single-core priority scheduling (ESP32-C6)
  - **Priority 3**: ESP-NOW sync broadcast task
  - **Highest priority**: State machine execution engine

- **Thread-Safe Double Buffering**: Configuration updates don't interrupt execution
- **Intelligent Delay Strategy**:
  - Yields to scheduler for waits >2ms
  - Busy-waits for <2ms transitions (minimal jitter)

### State Machine

Each device independently executes a state sequence synchronized via ESP-NOW:

```c
struct StateNode {
  bool digital_out1;     // GPIO 5 state
  bool digital_out2;     // GPIO 23 state
  bool digital_out3;     // GPIO 22 state
  uint8_t pwm_out;       // GPIO 4 duty cycle (0-255)
  uint32_t duration_ms;  // State duration
};
```

## Configuration

### Step 1: Update WiFi Credentials

Edit the active `WIFI_SSID` and `WIFI_PASSWORD` values in the `HOME` or `#else`
configuration block of `esp32_c6.ino`. Select the active block with:

```cpp
#define HOME 0
```

### Step 2: Update Server Configuration

Edit `SERVER_URL` and `API_KEY` in the same active configuration block.

```cpp
const char* SERVER_URL = "http://192.168.1.100:8000";  // Your server IP
const char* API_KEY    = "super-secret-admin";          // Match server key
```

### Step 3: Verify Pin Assignment

The pin mapping is compiled into the firmware. If your hardware uses different
GPIO pins, update these constants:

```cpp
static const int PIN_DIGITAL_OUT1 = 5;
static const int PIN_DIGITAL_OUT2 = 23;
static const int PIN_DIGITAL_OUT3 = 22;
static const int PIN_PWM_OUT      = 4;
```

## Building and Flashing

### Requirements
- **PlatformIO**: Install via VSCode extension or CLI
- **USB Cable**: For flashing firmware to ESP32

### Build Commands

```bash
# Build firmware
pio run

# Flash to device
pio run --target upload

# Open serial monitor
pio device monitor

# Build + Flash + Monitor (one command)
pio run --target upload && pio device monitor
```

### First Boot Sequence

1. Device connects to WiFi
2. Generates unique ID from MAC: `ESP32-C6-XXXX`
3. Registers with server via HTTP POST
4. Initializes ESP-NOW (default: follower mode)
5. Creates FreeRTOS tasks
6. Begins polling for configuration

## Expected Serial Output

```
========================================
Kywo - Production Firmware v3.0.0
Distributed ESP32 Control System
========================================

[hw] Hardware initialized:
  Digital outputs: GPIO 5, 23, 22
  PWM output: GPIO 4 (5000 Hz)
  Static HIGH: GPIO 7, Static LOW: GPIO 21
[wifi] Connecting to MyWiFi
[wifi] Connected! IP: 192.168.1.42, Channel: 1
[boot] Device ID: ESP32-C6-A3B4
[server] Registering as ESP32-C6-A3B4...
[server] Registration successful
[ESP-NOW] Initialized successfully
[ESP-NOW] Role: FOLLOWER (listening on channel 1)
[boot] FreeRTOS tasks created:
  - ESP-NOW sync task (Priority 3)
  - State machine engine (Highest Priority)

[boot] System ready. Waiting for configuration...

[config] New configuration detected. Parsing...
[config] SUCCESS! 2 states, 2000 ms total, PWM enabled
[ESP-NOW] Clock synchronized. Offset: -1234 us
[status] Running: 2 states, Master: NO
```

## Network Protocol Details

### Device Registration
```http
POST /devices/register
Content-Type: application/json

{
  "device_id": "ESP32-C6-A3B4",
  "device_token": "kywo-device-token",
  "firmware_version": "3.0.0-Production",
  "wifi_channel": 1
}
```

### Configuration Polling
```http
GET /devices/ESP32-C6-A3B4/config
x-api-key: super-secret-admin

Response:
{
  "sequence": [
    {
      "digital_out1": true,
      "digital_out2": false,
      "digital_out3": false,
      "pwm_out": 128,
      "duration_ms": 1000
    },
    {
      "digital_out1": false,
      "digital_out2": true,
      "digital_out3": true,
      "pwm_out": 255,
      "duration_ms": 1000
    }
  ],
  "is_master": false,
  "master_channel": 1
}
```

### ESP-NOW Sync Message
```c
struct sync_message_t {
  uint32_t magic;           // 0xA2C22026
  int64_t master_time_us;   // Grandmaster timestamp (us)
};
```

The master sends one broadcast every 500ms. A follower combines the master
timestamp with its calibrated one-way latency estimate, rejects samples more
than 500us from its current offset, and applies one quarter of each accepted
correction to limit radio-induced phase jitter. No ESP-NOW response packets are
sent by followers.

`LATENCY_COMPENSATION_US` is a hardware- and environment-dependent calibration
value. Start with 625us, measure the persistent observer-reported phase bias,
then adjust and repeat the hardware synchronization test.

## Troubleshooting

### Issue: Device not connecting to WiFi
- Verify SSID and password in firmware
- Check WiFi is 2.4GHz (ESP32-C6 doesn't support 5GHz)
- Serial output shows connection attempts

### Issue: Device not appearing in web dashboard
- Verify server URL and API key match
- Check device successfully registered (serial: `[server] Registration successful`)
- Refresh device list in web UI

### Issue: "Waiting for ESP-NOW clock sync..."
- Ensure at least one device is configured as Grandmaster via web UI
- Check all devices are on the same WiFi channel
- Serial should show: `[ESP-NOW] Clock synchronized. Offset: ... us`

### Issue: State transitions not synchronized
- Verify all devices show clock sync in serial output
- Check network latency (should be <5ms for WiFi)
- Ensure no WiFi interference on the channel

### Issue: PWM output not working
- Verify GPIO 4 is connected correctly
- Check PWM duty cycle is not 0 in sequence
- Test with simple sequence (pwm_out: 128 for 50% duty cycle)

## Performance Targets

These are design targets and require hardware-observer validation; they are not
guaranteed by the firmware alone.

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Clock sync drift | <50µs mean | Hardware observer (arch2_sync_test) |
| State transition jitter | <10µs | Oscilloscope on GPIO outputs |
| Config update latency | <1.5s | HTTP polling interval + parsing |
| ESP-NOW broadcast latency | ~1ms | Median transmission time |

## Firmware Architecture Improvements over POC

1. **Fixed Hardware Configuration**: Eliminates dynamic pin mapping overhead
2. **PWM Support**: LEDC peripheral for smooth analog output
3. **Single-Core Priority Scheduling**: Timing-critical execution has the highest task priority
4. **Enhanced Comments**: Production-ready documentation
5. **Updated Endpoints**: Uses simplified `/devices/` API (not `/arch2/devices/`)
6. **Version Tracking**: Semantic versioning for compatibility management

## License

Part of the Kywo Distributed Control System.  
See repository root for license information.

## Version History

- **3.0.0-Production** (March 17, 2026)
  - Production release based on POC testing
  - Fixed configuration: 3 digital + 1 PWM output
  - Improved state machine execution engine
  - Updated API endpoints for simplified server architecture
