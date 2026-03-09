// src/config.js
// Central config for API URLs and other constants

const API_BASE_URL = "http://127.0.0.1:8000";

export default {
  API_BASE_URL,
  SENSOR_DATA_URL: `${API_BASE_URL}/sensor-data`,
  TANK_PARAMETERS_URL: `${API_BASE_URL}/tank-parameters`,
};
