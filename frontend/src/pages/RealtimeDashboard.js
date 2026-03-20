import React, { useState, useEffect } from 'react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import WebSocketManager from '../services/websocket';
import './RealtimeDashboard.css';

const RealtimeDashboard = () => {
  const [predictions, setPredictions] = useState([]);
  const [sensorData, setSensorData] = useState([]);
  const [wsConnected, setWsConnected] = useState(false);

  useEffect(() => {
    // Initialize WebSocket (backend must support this)
    const ws = new WebSocketManager('ws://localhost:8000/ws/predictions');

    ws.connect()
      .then(() => {
        setWsConnected(true);
        
        // Subscribe to predictions
        const unsubscribe = ws.subscribe((data) => {
          setPredictions(prev => [...prev, data].slice(-50)); // Keep last 50
          setSensorData(prev => [...prev, {
            time: new Date().toLocaleTimeString(),
            distance: data.distance,
            temperature: data.temperature,
            confidence: data.confidence * 100
          }].slice(-20)); // Keep last 20
        });

        return unsubscribe;
      })
      .catch(err => {
        console.error('WebSocket connection failed:', err);
        setWsConnected(false);
      });

    return () => ws.disconnect();
  }, []);

  return (
    <div className="realtime-dashboard">
      <div className="status-bar">
        <h2>Real-time Predictions Dashboard</h2>
        <div className={`status-indicator ${wsConnected ? 'connected' : 'disconnected'}`}>
          {wsConnected ? '🟢 Connected' : '🔴 Disconnected'}
        </div>
      </div>

      <div className="predictions-container">
        <div className="predictions-list">
          <h3>Latest Predictions</h3>
          <div className="predictions-scroll">
            {predictions.map((pred, idx) => (
              <div key={idx} className="prediction-item">
                <span className="prediction-class">{pred.prediction}</span>
                <span className="prediction-confidence">{(pred.confidence * 100).toFixed(1)}%</span>
              </div>
            ))}
          </div>
        </div>

        <div className="chart-container">
          <h3>24-Hour Trends</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={sensorData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="time" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="distance" stroke="#8884d8" />
              <Line type="monotone" dataKey="temperature" stroke="#82ca9d" />
              <Line type="monotone" dataKey="confidence" stroke="#ffc658" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  );
};

export default RealtimeDashboard;