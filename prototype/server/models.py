from datetime import datetime
from pydantic import BaseModel, Field


class DeviceRegistrationRequest(BaseModel):
    """Request to register a new device."""
    device_id: str = Field(min_length=3, max_length=64)
    device_token: str = Field(min_length=8, max_length=128)
    firmware_version: str | None = None
    wifi_channel: int | None = None


class SensorReading(BaseModel):
    """Latest analog sensor sample reported by a device."""
    raw: int = Field(ge=0, le=4095)
    millivolts: int | None = Field(default=None, ge=0, le=3300)
    sampled_at_us: int = Field(ge=0)


class DeviceTelemetryRequest(BaseModel):
    """Telemetry submitted by a device."""
    sensor: SensorReading


class DeviceRecord(BaseModel):
    """Device registration and status record."""
    device_id: str
    device_token: str
    firmware_version: str | None = None
    last_seen: datetime
    is_master: bool = False
    wifi_channel: int | None = None
    sensor: SensorReading | None = None
    sensor_received_at: datetime | None = None


class DeviceStatus(BaseModel):
    """Enhanced device record with online status."""
    device_id: str
    device_token: str
    firmware_version: str | None = None
    last_seen: datetime
    is_master: bool = False
    wifi_channel: int | None = None
    sensor: SensorReading | None = None
    sensor_received_at: datetime | None = None
    is_online: bool
    seconds_since_seen: float
