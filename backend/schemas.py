from __future__ import annotations
from typing import Optional
from pydantic import BaseModel, Field, field_validator

class AnalyzeRequest(BaseModel):
    crop: str = "tomato"
    condition: str = "healthy"
    field_id: Optional[int] = None
    growth_stage: str = "vegetative"
    soil_moisture: float = Field(45, ge=0, le=100)
    temperature: float = Field(29, ge=-20, le=70)
    humidity: float = Field(55, ge=0, le=100)
    weather: str = "normal"
    recent_rainfall_mm: float = Field(0, ge=0, le=500)
    recent_irrigation_hours: float = Field(24, ge=0, le=720)
    connectivity: str = "offline"
    sensor_reliability: float = Field(1, ge=0, le=1)
    image_quality: float = Field(1, ge=0, le=1)
    image_ref: Optional[str] = None
    source: str = "simulator"
    client_event_id: Optional[str] = Field(None, max_length=120)

    @field_validator('crop','growth_stage','weather','connectivity','condition')
    @classmethod
    def safe_text(cls, v):
        v=str(v).strip().lower()
        if len(v)>80: raise ValueError('field too long')
        return v

class SensorRequest(BaseModel):
    device_id: str = Field(min_length=1, max_length=80)
    field_id: Optional[int] = None
    soil_moisture: Optional[float] = Field(None, ge=-20, le=120)
    temperature: Optional[float] = Field(None, ge=-80, le=100)
    humidity: Optional[float] = Field(None, ge=-20, le=120)
    timestamp: Optional[float] = None
    firmware_version: Optional[str] = Field(None, max_length=80)
    battery: Optional[float] = Field(None, ge=0, le=100)

class FeedbackRequest(BaseModel):
    observation_id: Optional[int] = None
    useful: bool
    label: str = Field('', max_length=80)
    note: str = Field('', max_length=500)

class MultimodalMeta(BaseModel):
    crop: str = 'tomato'
    field_id: Optional[int] = None
    growth_stage: str = 'vegetative'
    soil_moisture: float = Field(45, ge=0, le=100)
    temperature: float = Field(29, ge=-20, le=70)
    humidity: float = Field(55, ge=0, le=100)
    weather: str = 'normal'
    recent_rainfall_mm: float = Field(0, ge=0, le=500)
    recent_irrigation_hours: float = Field(24, ge=0, le=720)
    connectivity: str = 'online'
    sensor_reliability: float = Field(1, ge=0, le=1)

class IrrigationRequest(BaseModel):
    field_id: Optional[int] = None
    observation_id: Optional[int] = None
    duration_min: float = Field(0, ge=0, le=180)
    reason: str = Field('', max_length=500)
    simulate: bool = True


class FarmerProfileRequest(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    crops: list[str] = Field(default_factory=list, min_length=1, max_length=12)
    state: str = Field('', max_length=80)
    district: str = Field('', max_length=80)
    latitude: Optional[float] = Field(None, ge=6, le=38)
    longitude: Optional[float] = Field(None, ge=68, le=98)
    location_source: str = Field('manual', max_length=30)
    field_name: str = Field('My Field', max_length=80)
    area_acres: Optional[float] = Field(None, ge=0, le=100000)
    soil_type: str = Field('unknown', max_length=40)
