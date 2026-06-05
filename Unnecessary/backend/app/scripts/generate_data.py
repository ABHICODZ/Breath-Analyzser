import asyncio
from datetime import datetime, timedelta
import random
from sqlalchemy import text
from app.db.database import engine
from app.services.osmnx_engine import CityGraphExtractor
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def generate_mock_sensor_data(place_name="Hoboken, New Jersey, USA"):
    """
    Since we don't have active CPCB/OpenAQ API keys or live satellite data in this tutorial,
    this script acts as our Data Ingestion Engine (Step 3 & 4). 
    It generates realistic time-series pollution data mapped to the city graph.
    """
    logger.info(f"Extracting spatial grid for {place_name}...")
    
    # 1. Get the spatial environment
    extractor = CityGraphExtractor(place_name)
    extractor.extract_infrastructure()
    extractor.calculate_canyon_metrics()
    G = extractor.get_graph()
    
    if not G:
        logger.error("Failed to extract graph. Cannot generate data.")
        return

    # Extract 50 random nodes from the graph to act as our "Virtual Ground Sensors"
    all_nodes = list(G.nodes(data=True))
    virtual_sensors = random.sample(all_nodes, min(50, len(all_nodes)))
    
    logger.info(f"Generated {len(virtual_sensors)} Virtual Ground Sensors.")

    # 2. Insert Sensor Locations into DB
    async with engine.begin() as conn:
        logger.info("Initializing TimescaleDB Schema (if not exists)...")
        with open("app/db/init.sql", "r") as f:
            sql_script = f.read()
        await conn.execute(text(sql_script))

        logger.info("Inserting static sensor locations...")
        for node_id, data in virtual_sensors:
            lat = data.get('y', 0.0)
            lon = data.get('x', 0.0)
            # Insert logic using standard SQL since we bypassed ORM for raw speed required by Time-Series
            insert_loc_sql = """
            INSERT INTO location_nodes (node_id, lat, lon)
            VALUES (:node_id, :lat, :lon)
            ON CONFLICT (node_id) DO NOTHING;
            """
            await conn.execute(text(insert_loc_sql), {"node_id": node_id, "lat": lat, "lon": lon})


    # 3. Generate 7 Days of Historical Time-Series Data
    logger.info("Generating 7 days of historical pollution data...")
    end_time = datetime.now()
    start_time = end_time - timedelta(days=7)
    
    total_records = 0
    
    async with engine.begin() as conn:
        current_time = start_time
        while current_time <= end_time:
            # Generate data for every hour
            
            # Simulate a daily pollution curve (worse during rush hours: 8am and 5pm)
            hour = current_time.hour
            rush_hour_factor = 2.0 if (7 <= hour <= 9) or (16 <= hour <= 19) else 1.0
            
            for node_id, data in virtual_sensors:
                # Base pollution depends on street topology (Aspect Ratio & SVF)
                # Narrower streets (low width, high height) have higher base pollution
                svf = data.get('svf', 0.5)
                topology_trap_factor = (1.0 - svf) + 0.5 
                
                # PM2.5 generally ranges from 5 (clean) to 150+ (very unhealthy)
                base_pm25 = 15.0 * topology_trap_factor * rush_hour_factor
                # Add some random noise
                pm2_5 = max(1.0, base_pm25 + random.uniform(-5.0, 10.0))
                
                insert_data_sql = """
                INSERT INTO air_quality_data (time, node_id, pm2_5, pm10, no2, temperature, humidity, source)
                VALUES (:time, :node_id, :pm2_5, :pm10, :no2, :temp, :hum, :source);
                """
                
                await conn.execute(text(insert_data_sql), {
                    "time": current_time,
                    "node_id": node_id,
                    "pm2_5": pm2_5,
                    "pm10": pm2_5 * 1.5, # Rough correlation
                    "no2": pm2_5 * 0.8,
                    "temp": 20.0 + random.uniform(-5.0, 5.0),
                    "hum": 50.0 + random.uniform(-10.0, 10.0),
                    "source": "simulated_sensor"
                })
                total_records += 1
                
            current_time += timedelta(hours=1)
            
    logger.info(f"✅ Successfully ingested {total_records} hourly records into TimescaleDB Hypertable.")

if __name__ == "__main__":
    asyncio.run(generate_mock_sensor_data())
