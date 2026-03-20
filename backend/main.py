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

TEST_MODE = os.environ.get("TEST_MODE", "True").lower() == "true"
NODE_ID = os.environ.get("NODE_ID", "NODE_001")
DATA_COLLECTION_INTERVAL = int(os.environ.get("DATA_COLLECTION_INTERVAL", "20"))
THINGSPEAK_URL = os.environ.get(
    "THINGSPEAK_URL",
    "https://api.thingspeak.com/channels/3290444/feeds.json?api_key=AWP8F08WA7SLO5EQ&results=-1"
)

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


# ==============================
# SENSOR DATA COLLECTOR
# ==============================

def sensor_collector():
    """Background thread that continuously collects sensor data"""
    print("\n[COLLECTOR] Started\n")

    while True:
        try:
            if TEST_MODE:
                test_data = generate_test_data()
                distance = test_data["distance"]
                temperature = test_data["temperature"]
                timestamp = test_data["timestamp"]
            else:
                try:
                    response = requests.get(THINGSPEAK_URL, timeout=10)
                    data = response.json()
                    
                    if not data.get("feeds"):
                        time.sleep(DATA_COLLECTION_INTERVAL)
                        continue
                    
                    feed = data["feeds"][0]
                    distance = float(feed.get("field1", 0))
                    temperature = float(feed.get("field2", 0))
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                except Exception as e:
                    print(f"[COLLECTOR] Error: {e}")
                    time.sleep(DATA_COLLECTION_INTERVAL)
                    continue

            conn = get_connection()
            cur = conn.cursor()
            cur.execute(
                "INSERT INTO sensor_data (node_id, field1, field2, created_at) VALUES (%s, %s, %s, %s)",
                (NODE_ID, distance, temperature, timestamp)
            )
            conn.commit()
            cur.close()
            conn.close()

            print(f"[COLLECTOR] distance={distance}cm, temp={temperature}°C")

        except Exception as e:
            print(f"[COLLECTOR] Error: {e}")

        time.sleep(DATA_COLLECTION_INTERVAL)


# ==============================
# ENDPOINTS - SENSOR DATA
# ==============================

@app.get("/sensor-data", response_model=list[SensorReading], tags=["Sensor Data"])
def get_sensor_data(node_id: str = None):
    """Get sensor readings with optional filtering by node_id"""
    try:
        conn = get_connection()
        cur = conn.cursor()

        if node_id:
            cur.execute(
                "SELECT id, node_id, field1, field2, created_at FROM sensor_data WHERE node_id = %s ORDER BY created_at DESC LIMIT 100",
                (node_id,)
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
# ENDPOINTS - SYSTEM
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


@app.get("/", tags=["System"])
def root():
    """API information endpoint"""
    return {
        "name": "IoT Water Tank Monitoring API",
        "version": "2.0.0",
        "description": "Backend with ML water activity prediction",
        "docs": "http://localhost:8000/docs",
        "health": "http://localhost:8000/health",
        "ml_enabled": TF_AVAILABLE
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