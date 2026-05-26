import os
from dotenv import load_dotenv
import requests
import psycopg2
import time
import random
import threading
from datetime import datetime
import numpy as np
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from auth_routes import router as auth_router


try:
    from tensorflow.keras.models import load_model
    TF_AVAILABLE = True
except ImportError:
    TF_AVAILABLE = False
    print("[WARNING] TensorFlow not installed. ML features disabled.")

load_dotenv()

app = FastAPI(
    title="IoT Water Tank Monitoring API",
    description="Backend service for IoT sensor data with ML predictions",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


app.include_router(auth_router)



# ==============================
# GLOBALS
# ==============================

ml_model = None
MODEL_CLASSES = ["no_activity","filling","flush","washing_machine","geyser"]
MODEL_INFO = {
    "model_type": "LSTM",
    "version": "1.0",
    "accuracy": 0.98,
    "last_trained": "2026-03-20",
    "classes": MODEL_CLASSES
}

# Track data source
data_source_stats = {
    "thingspeak_success": 0,
    "thingspeak_failures": 0,
    "test_data_used": 0,
    "last_error": None,
    "current_mode": "UNKNOWN"
}

# ==============================
# DATABASE
# ==============================

def get_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "iot-test"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD", "BAT"),
        sslmode=os.environ.get("DB_SSLMODE", "prefer")
    )


def create_tables():
    """Create all necessary database tables"""
    conn = get_connection()
    cur = conn.cursor()

    # Sensor data table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS sensor_data (
        id SERIAL PRIMARY KEY,
        node_id VARCHAR(50),
        field1 FLOAT,
        field2 FLOAT,
        data_source VARCHAR(20) DEFAULT 'unknown',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Tank parameters table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS tank_sensorparameters (
        id SERIAL PRIMARY KEY,
        node_id VARCHAR(50) UNIQUE,
        tank_height_cm FLOAT,
        tank_length_cm FLOAT,
        tank_width_cm FLOAT,
        lat FLOAT,
        long FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Predictions history table
    cur.execute("""
    CREATE TABLE IF NOT EXISTS predictions (
        id SERIAL PRIMARY KEY,
        node_id VARCHAR(50),
        distance FLOAT,
        temperature FLOAT,
        prediction VARCHAR(50),
        confidence FLOAT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)

    # Create indexes for faster queries
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_node ON sensor_data(node_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_time ON sensor_data(created_at DESC)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_sensor_source ON sensor_data(data_source)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_node ON predictions(node_id)")
    cur.execute("CREATE INDEX IF NOT EXISTS idx_pred_time ON predictions(created_at DESC)")

    conn.commit()
    cur.close()
    conn.close()
    print("[DB] Tables initialized")


def load_ml_model():
 
    global ml_model
    
    if not TF_AVAILABLE:
        print("[ML] TensorFlow not available")
        return False
    
    try:
        model_path = os.environ.get("MODEL_PATH", "saved_models/LSTM_model.h5")
        
        if not os.path.exists(model_path):
            print(f"[ML] Model not found at {model_path}")
            print(f"[ML] Please place your model at: {os.path.abspath(model_path)}")
            return False
        
        ml_model = load_model(model_path)
        print(f"[ML] Model loaded from {model_path}")
        return True
        
    except Exception as e:
        print(f"[ML] Error loading model: {e}")
        return False


# ==============================
# CONFIG
# ==============================

# IMPORTANT: Set TEST_MODE to False to read actual sensor data from ThingSpeak
TEST_MODE = os.environ.get("TEST_MODE", "false").lower() == "true"

NODE_ID = os.environ.get("NODE_ID", "NODE_001")
DATA_COLLECTION_INTERVAL = int(os.environ.get("DATA_COLLECTION_INTERVAL", "20"))
THINGSPEAK_URL = os.environ.get(
    "THINGSPEAK_URL",
    "https://api.thingspeak.com/channels/3120638/feeds.json?api_key=CXEN9P2CMZ1HOJDL&results=5"
)
THINGSPEAK_TIMEOUT = int(os.environ.get("THINGSPEAK_TIMEOUT", "15"))

# ==============================
# PYDANTIC MODELS
# ==============================

class SensorReading(BaseModel):
    id: int
    node_id: str
    distance: float
    temperature: float
    created_at: str


class TankParameters(BaseModel):
    node_id: str
    tank_height_cm: float
    tank_length_cm: float
    tank_width_cm: float
    lat: float
    long: float


class TankParametersResponse(BaseModel):
    id: int
    node_id: str
    tank_height_cm: float
    tank_length_cm: float
    tank_width_cm: float
    lat: float
    long: float


class PredictionRequest(BaseModel):
    """Request model for predictions"""
    distance: float
    temperature: float
    node_id: str = "NODE_001"
    time_features: list = None


class PredictionResponse(BaseModel):
    """Response model for predictions"""
    prediction: str
    confidence: float
    distance: float
    temperature: float
    node_id: str
    timestamp: str


class PredictionHistory(BaseModel):
    """Model for prediction history"""
    id: int
    node_id: str
    distance: float
    temperature: float
    prediction: str
    confidence: float
    created_at: str


class ModelInfoResponse(BaseModel):
    """Model information response"""
    model_type: str
    version: str
    accuracy: float
    last_trained: str
    classes: list
    status: str
    tensorflow_available: bool


# ==============================
# HELPER FUNCTIONS
# ==============================

def generate_test_data():
    """Generate random test sensor data"""
    return {
        "distance": round(94.0 + random.uniform(-10, 10), 1),
        "temperature": round(20.8 + random.uniform(-2, 2), 1),
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }


def fetch_thingspeak_data():
    """
    Fetch data from ThingSpeak API
    Returns: (success: bool, distance: float, temperature: float, error_msg: str)
    """
    try:
        print(f"[THINGSPEAK] Fetching from: {THINGSPEAK_URL[:80]}...")
        response = requests.get(THINGSPEAK_URL, timeout=THINGSPEAK_TIMEOUT)
        response.raise_for_status()
        
        data = response.json()
        
        # Validate response structure
        if not isinstance(data, dict):
            error_msg = f"Invalid response type: {type(data)}"
            print(f"[THINGSPEAK] ✗ {error_msg}")
            return False, 0, 0, error_msg
        
        if "feeds" not in data or not data["feeds"]:
            error_msg = "No feeds in response - channel may be empty"
            print(f"[THINGSPEAK] ✗ {error_msg}")
            return False, 0, 0, error_msg
        
        # Get latest feed
        feed = data["feeds"][0]
        
        # Extract and validate field1 (distance)
        field1_raw = feed.get("field1")
        if field1_raw is None or field1_raw == "":
            error_msg = f"field1 is empty/null: {field1_raw}"
            print(f"[THINGSPEAK] ✗ {error_msg}")
            return False, 0, 0, error_msg
        
        try:
            distance = float(field1_raw)
        except ValueError as e:
            error_msg = f"field1 not a valid number: {field1_raw}"
            print(f"[THINGSPEAK] ✗ {error_msg}")
            return False, 0, 0, error_msg
        
        # Extract and validate field2 (temperature)
        field2_raw = feed.get("field2")
        if field2_raw is None or field2_raw == "":
            error_msg = f"field2 is empty/null: {field2_raw}"
            print(f"[THINGSPEAK] ✗ {error_msg}")
            return False, 0, 0, error_msg
        
        try:
            temperature = float(field2_raw)
        except ValueError as e:
            error_msg = f"field2 not a valid number: {field2_raw}"
            print(f"[THINGSPEAK] ✗ {error_msg}")
            return False, 0, 0, error_msg
        
        print(f"[THINGSPEAK] ✓ Retrieved: distance={distance}, temp={temperature}")
        return True, distance, temperature, None
    
    except requests.exceptions.Timeout:
        error_msg = f"Request timeout ({THINGSPEAK_TIMEOUT}s) - ThingSpeak unreachable"
        print(f"[THINGSPEAK] ✗ {error_msg}")
        return False, 0, 0, error_msg
    
    except requests.exceptions.ConnectionError as e:
        error_msg = f"Connection error: {str(e)[:100]}"
        print(f"[THINGSPEAK] ✗ {error_msg}")
        return False, 0, 0, error_msg
    
    except requests.exceptions.HTTPError as e:
        error_msg = f"HTTP error: {e.response.status_code} - {e.response.reason}"
        print(f"[THINGSPEAK] ✗ {error_msg}")
        return False, 0, 0, error_msg
    
    except ValueError as e:
        error_msg = f"Invalid JSON response: {str(e)[:100]}"
        print(f"[THINGSPEAK] ✗ {error_msg}")
        return False, 0, 0, error_msg
    
    except Exception as e:
        error_msg = f"Unexpected error: {str(e)[:100]}"
        print(f"[THINGSPEAK] ✗ {error_msg}")
        return False, 0, 0, error_msg


def preprocess_sensor_data(distance: float, temperature: float, time_features: list = None):
    
    # Normalize the data to 0-1 range
    distance_normalized = distance / 100.0
    temperature_normalized = temperature / 30.0
    
    sequence = np.array([[distance_normalized, temperature_normalized]] * 10)
    
    # Add batch dimension for model input
    sequence = np.expand_dims(sequence, axis=0)
    
    return sequence


def make_prediction(distance: float, temperature: float, time_features: list = None):
    
    global ml_model
    
    if ml_model is None:
        return {
            "prediction": "error",
            "confidence": 0.0,
            "error": "Model not loaded"
        }
    
    try:
        # Step 1: Preprocess input data
        input_data = preprocess_sensor_data(distance, temperature, time_features)
        
        # Step 2: Run model prediction
        prediction_probs = ml_model.predict(input_data, verbose=0)
        
        # Step 3: Return prediction label and confidence
        prediction_index = np.argmax(prediction_probs[0])
        confidence = float(prediction_probs[0][prediction_index])
        prediction_class = MODEL_CLASSES[prediction_index]
        
        return {
            "prediction": prediction_class,
            "confidence": confidence
        }
    
    except Exception as e:
        print(f"[ML] Prediction error: {e}")
        return {
            "prediction": "error",
            "confidence": 0.0,
            "error": str(e)
        }


def save_prediction_to_db(node_id: str, distance: float, temperature: float, 
                         prediction: str, confidence: float):
    """Save prediction result to database"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO predictions (node_id, distance, temperature, prediction, confidence) VALUES (%s, %s, %s, %s, %s)",
            (node_id, distance, temperature, prediction, confidence)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[DB] Error saving prediction: {e}")


def save_sensor_data(node_id: str, distance: float, temperature: float, 
                    data_source: str = "unknown", timestamp: str = None):
    """Save sensor data to database with source tracking"""
    if timestamp is None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    try:
        conn = get_connection()
        cur = conn.cursor()
        
        cur.execute(
            "INSERT INTO sensor_data (node_id, field1, field2, data_source, created_at) VALUES (%s, %s, %s, %s, %s)",
            (node_id, distance, temperature, data_source, timestamp)
        )
        
        conn.commit()
        cur.close()
        conn.close()
        
    except Exception as e:
        print(f"[DB] Error saving sensor data: {e}")


# ==============================
# SENSOR DATA COLLECTOR
# ==============================

def sensor_collector():
    """Background thread that continuously collects sensor data from ThingSpeak or test mode"""
    print("\n[COLLECTOR] ========================================")
    print(f"[COLLECTOR] TEST_MODE: {TEST_MODE}")
    print(f"[COLLECTOR] Collection Interval: {DATA_COLLECTION_INTERVAL}s")
    print(f"[COLLECTOR] Node ID: {NODE_ID}")
    if not TEST_MODE:
        print(f"[COLLECTOR] ThingSpeak Timeout: {THINGSPEAK_TIMEOUT}s")
        # Mask API key for security
        masked_url = THINGSPEAK_URL.replace(
            THINGSPEAK_URL.split("api_key=")[1].split("&")[0] if "api_key=" in THINGSPEAK_URL else "",
            "***MASKED***"
        )
        print(f"[COLLECTOR] URL: {masked_url[:80]}...")
    print("[COLLECTOR] ========================================\n")

    while True:
        try:
            if TEST_MODE:
                # Generate synthetic test data
                test_data = generate_test_data()
                distance = test_data["distance"]
                temperature = test_data["temperature"]
                timestamp = test_data["timestamp"]
                data_source = "TEST"
                
                print(f"[COLLECTOR] [TEST] distance={distance}cm, temp={temperature}°C")
                data_source_stats["test_data_used"] += 1
                data_source_stats["current_mode"] = "TEST_MODE"
            
            else:
                # Fetch real data from ThingSpeak
                success, distance, temperature, error_msg = fetch_thingspeak_data()
                
                if success:
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    data_source = "THINGSPEAK"
                    data_source_stats["thingspeak_success"] += 1
                    data_source_stats["current_mode"] = "LIVE_DATA"
                    print(f"[COLLECTOR] [LIVE] distance={distance}cm, temp={temperature}°C")
                
                else:
                    # ThingSpeak failed, use test data as fallback
                    data_source_stats["thingspeak_failures"] += 1
                    data_source_stats["last_error"] = error_msg
                    
                    print(f"[COLLECTOR] [FALLBACK] Using test data due to ThingSpeak error")
                    test_data = generate_test_data()
                    distance = test_data["distance"]
                    temperature = test_data["temperature"]
                    timestamp = test_data["timestamp"]
                    data_source = "TEST_FALLBACK"
                    data_source_stats["test_data_used"] += 1
                    print(f"[COLLECTOR] [FALLBACK] distance={distance}cm, temp={temperature}°C")

            # Save to database with source tracking
            save_sensor_data(NODE_ID, distance, temperature, data_source, timestamp)
            
            # Print statistics every 10 collections
            if (data_source_stats["thingspeak_success"] + data_source_stats["test_data_used"]) % 10 == 0:
                print(f"[COLLECTOR] Stats - Live: {data_source_stats['thingspeak_success']}, "
                      f"Test: {data_source_stats['test_data_used']}, "
                      f"Errors: {data_source_stats['thingspeak_failures']}")

        except Exception as e:
            print(f"[COLLECTOR] Unexpected error: {e}")

        time.sleep(DATA_COLLECTION_INTERVAL)


# ==============================
# ENDPOINTS - SENSOR DATA
# ==============================

@app.get("/sensor-data", response_model=list[SensorReading], tags=["Sensor Data"])
def get_sensor_data(node_id: str = None, source: str = None):
    """Get sensor readings with optional filtering by node_id and data source"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        if node_id and source:
            cur.execute(
                "SELECT id, node_id, field1, field2, created_at FROM sensor_data WHERE node_id = %s AND data_source = %s ORDER BY created_at DESC LIMIT 100",
                (node_id, source)
            )
        elif node_id:
            cur.execute(
                "SELECT id, node_id, field1, field2, created_at FROM sensor_data WHERE node_id = %s ORDER BY created_at DESC LIMIT 100",
                (node_id,)
            )
        elif source:
            cur.execute(
                "SELECT id, node_id, field1, field2, created_at FROM sensor_data WHERE data_source = %s ORDER BY created_at DESC LIMIT 100",
                (source,)
            )
        else:
            cur.execute(
                "SELECT id, node_id, field1, field2, created_at FROM sensor_data ORDER BY created_at DESC LIMIT 100"
            )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": row[0],
                "node_id": row[1],
                "distance": row[2],
                "temperature": row[3],
                "created_at": str(row[4])
            }
            for row in rows
        ]

    except Exception as e:
        print(f"[API] Error: {e}")
        return []


@app.get("/sensor-data/by-source", tags=["Sensor Data"])
def get_sensor_data_by_source():
    """Get sensor data summary grouped by source (LIVE vs TEST)"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT 
                data_source,
                COUNT(*) as count,
                AVG(field1) as avg_distance,
                AVG(field2) as avg_temperature,
                MAX(created_at) as last_reading
            FROM sensor_data
            GROUP BY data_source
            ORDER BY last_reading DESC
        """)

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return {
            "summary": [
                {
                    "source": row[0],
                    "count": row[1],
                    "avg_distance": round(row[2], 2) if row[2] else 0,
                    "avg_temperature": round(row[3], 2) if row[3] else 0,
                    "last_reading": str(row[4])
                }
                for row in rows
            ]
        }

    except Exception as e:
        print(f"[API] Error: {e}")
        return {"summary": []}


# ==============================
# ENDPOINTS - TANK PARAMETERS
# ==============================

@app.post("/tank-parameters", tags=["Tank Configuration"])
def create_tank_parameters(data: TankParameters):
    """Create new tank configuration"""
    conn = None
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute(
            "INSERT INTO tank_sensorparameters (node_id, tank_height_cm, tank_length_cm, tank_width_cm, lat, long) VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
            (data.node_id, data.tank_height_cm, data.tank_length_cm, data.tank_width_cm, data.lat, data.long)
        )

        new_id = cur.fetchone()[0]
        conn.commit()
        cur.close()
        conn.close()

        return {"message": "Tank parameters inserted successfully", "id": new_id, "status": "SUCCESS"}

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        return {"message": str(e), "status": "ERROR"}


@app.get("/tank-parameters", response_model=list[TankParametersResponse], tags=["Tank Configuration"])
def get_tank_parameters():
    """Get all tank configurations"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        cur.execute("SELECT id, node_id, tank_height_cm, tank_length_cm, tank_width_cm, lat, long FROM tank_sensorparameters ORDER BY id DESC")

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": row[0],
                "node_id": row[1],
                "tank_height_cm": row[2],
                "tank_length_cm": row[3],
                "tank_width_cm": row[4],
                "lat": row[5],
                "long": row[6]
            }
            for row in rows
        ]

    except Exception as e:
        print(f"[API] Error: {e}")
        return []


# ==============================
# ENDPOINTS - ML PREDICTIONS (NEW)
# ==============================

@app.post("/api/v1/predict", response_model=PredictionResponse, tags=["ML Predictions"])
def predict_water_activity(data: PredictionRequest):
    
    try:
        # Step 1: Preprocess input data
        result = make_prediction(data.distance, data.temperature, data.time_features)
        
        # Check if prediction was successful
        if result.get("error"):
            print(f"[API] Prediction error: {result['error']}")
        
        # Step 2 & 3: Run model and get prediction/confidence
        if result["prediction"] != "error":
            # Save successful prediction to database
            save_prediction_to_db(
                data.node_id,
                data.distance,
                data.temperature,
                result["prediction"],
                result["confidence"]
            )
        
        return {
            "prediction": result["prediction"],
            "confidence": result["confidence"],
            "distance": data.distance,
            "temperature": data.temperature,
            "node_id": data.node_id,
            "timestamp": datetime.now().isoformat()
        }
    
    except Exception as e:
        print(f"[API] Error: {e}")
        return {
            "prediction": "error",
            "confidence": 0.0,
            "distance": data.distance,
            "temperature": data.temperature,
            "node_id": data.node_id,
            "timestamp": datetime.now().isoformat()
        }


@app.get("/api/v1/model-info", response_model=ModelInfoResponse, tags=["ML Predictions"])
def get_model_info():

    return {
        "model_type": MODEL_INFO["model_type"],
        "version": MODEL_INFO["version"],
        "accuracy": MODEL_INFO["accuracy"],
        "last_trained": MODEL_INFO["last_trained"],
        "classes": MODEL_INFO["classes"],
        "status": "Loaded" if ml_model is not None else "Not loaded",
        "tensorflow_available": TF_AVAILABLE
    }


@app.get("/api/v1/predictions-history", response_model=list[PredictionHistory], tags=["ML Predictions"])
def get_predictions_history(node_id: str = None, limit: int = 100):
  
    try:
        conn = get_connection()
        cur = conn.cursor()

        if node_id:
            cur.execute(
                "SELECT id, node_id, distance, temperature, prediction, confidence, created_at FROM predictions WHERE node_id = %s ORDER BY created_at DESC LIMIT %s",
                (node_id, limit)
            )
        else:
            cur.execute(
                "SELECT id, node_id, distance, temperature, prediction, confidence, created_at FROM predictions ORDER BY created_at DESC LIMIT %s",
                (limit,)
            )

        rows = cur.fetchall()
        cur.close()
        conn.close()

        return [
            {
                "id": row[0],
                "node_id": row[1],
                "distance": row[2],
                "temperature": row[3],
                "prediction": row[4],
                "confidence": row[5],
                "created_at": str(row[6])
            }
            for row in rows
        ]

    except Exception as e:
        print(f"[API] Error: {e}")
        return []


# ==============================
# ENDPOINTS - SYSTEM & DIAGNOSTICS
# ==============================

@app.get("/health", tags=["System"])
def health_check():
    """Check API and database health status"""
    try:
        conn = get_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        cur.close()
        conn.close()

        return {
            "status": "healthy",
            "database": "connected",
            "ml_model": "loaded" if ml_model is not None else "not_loaded",
            "timestamp": datetime.now().isoformat()
        }

    except Exception as e:
        return {
            "status": "unhealthy",
            "database": "disconnected",
            "ml_model": "error",
            "error": str(e)
        }


@app.get("/diagnostics", tags=["System"])
def get_diagnostics():
    """Get system diagnostics and data collection statistics"""
    return {
        "test_mode": TEST_MODE,
        "current_mode": data_source_stats["current_mode"],
        "statistics": {
            "thingspeak_successful": data_source_stats["thingspeak_success"],
            "thingspeak_failures": data_source_stats["thingspeak_failures"],
            "test_data_used": data_source_stats["test_data_used"],
            "last_error": data_source_stats["last_error"]
        },
        "configuration": {
            "node_id": NODE_ID,
            "collection_interval_seconds": DATA_COLLECTION_INTERVAL,
            "thingspeak_timeout_seconds": THINGSPEAK_TIMEOUT
        }
    }


@app.get("/", tags=["System"])
def root():
    """API information endpoint"""
    return {
        "name": "IoT Water Tank Monitoring API",
        "version": "2.0.0",
        "description": "Backend with ML water activity prediction",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health",
        "diagnostics": "http://localhost:8000/diagnostics",
        "ml_enabled": TF_AVAILABLE,
        "test_mode": TEST_MODE
    }


# ==============================
# STARTUP
# ==============================

@app.on_event("startup")
def startup_event():
    """Initialize on application startup"""
    print("\n[STARTUP] Initializing database...")
    create_tables()
    
    print("[STARTUP] Loading ML model...")
    load_ml_model()
    
    print("[STARTUP] Starting sensor collector...\n")
    threading.Thread(target=sensor_collector, daemon=True).start()


# ==============================
# MAIN
# ==============================

if __name__ == "__main__":
    print("IoT Water Tank Backend - API Server with ML")
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
