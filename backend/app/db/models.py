from sqlalchemy import Column, String, Float, DateTime
from sqlalchemy.orm import declarative_base
import datetime

Base = declarative_base()

class SensorData(Base):
    __tablename__ = "sensor_data"

    # TimescaleDB requires the time column to be part of the primary key if we partition by it
    # But usually setting composite PK or simply no primary key works for raw time-series data
    time = Column(DateTime(timezone=True), primary_key=True, default=datetime.datetime.utcnow)
    sensor_id = Column(String(50), primary_key=True, index=True)
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    
    # Pollutants
    pm25 = Column(Float, nullable=True)
    pm10 = Column(Float, nullable=True)
    no2 = Column(Float, nullable=True)
    so2 = Column(Float, nullable=True)
    co = Column(Float, nullable=True)
    o3 = Column(Float, nullable=True)

    def __repr__(self):
        return f"<SensorData(sensor_id='{self.sensor_id}', time='{self.time}', pm25={self.pm25})>"
