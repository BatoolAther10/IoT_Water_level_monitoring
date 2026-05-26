import React, { useState, useEffect, useMemo, useCallback } from 'react';
import {
  LineChart, Line, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
} from 'recharts';
import axios from 'axios';
import config from '../config';

const Home = () => {
  const [waterLevel, setWaterLevel] = useState(0);
  const [temperature, setTemperature] = useState(0);
  const [waterLevelData, setWaterLevelData] = useState([]);
  const [temperatureData, setTemperatureData] = useState([]);
  const [nodes, setNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState('');

  const [prediction, setPrediction] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [predictionLoading, setPredictionLoading] = useState(false);
  const [predictionError, setPredictionError] = useState('');

  // -------------------------
  // NODE MAPPING
  // -------------------------
  const getActualTankId = (nodeId) => {
    const mapping = {
      'Node 1': 'NODE_001',
      'Node 2': 'NODE_002',
      'NODE_001': 'NODE_001'
    };
    return mapping[nodeId] || nodeId;
  };

  // -------------------------
  // FETCH SENSOR DATA
  // -------------------------
  const fetchSensorData = useCallback(async () => {
    if (!selectedNode) return;
    try {
      const response = await axios.get(config.SENSOR_DATA_URL);
      const allSensorData = response.data || [];

      const actualNodeId = getActualTankId(selectedNode);
      const sensorData = allSensorData.filter(
        (item) => item.node_id === actualNodeId
      );

      if (sensorData.length > 0) {
        const latest = sensorData[0];

        const selectedNodeData = nodes.find(n => n.id === selectedNode);
        const tankHeight = selectedNodeData?.tank_height || 200;

        const waterLevelPercentage = Math.min(
          100,
          Math.round(((tankHeight - latest.distance) / tankHeight) * 100)
        );

        setWaterLevel(waterLevelPercentage);
        setTemperature(Math.round(latest.temperature * 10) / 10);

        const reversed = [...sensorData].reverse();

        setWaterLevelData(
          reversed.map(item => ({
            time: new Date(item.created_at).toLocaleTimeString(),
            value: Math.min(
              100,
              Math.round(((tankHeight - item.distance) / tankHeight) * 100)
            ),
            raw_cm: item.distance
          }))
        );

        setTemperatureData(
          reversed.map(item => ({
            time: new Date(item.created_at).toLocaleTimeString(),
            value: Math.round(item.temperature * 10) / 10
          }))
        );

      } else {
        setWaterLevel(0);
        setTemperature(0);
        setWaterLevelData([]);
        setTemperatureData([]);
      }

    } catch (error) {
      console.error(error);
    }
  }, [selectedNode, nodes]);

  // -------------------------
  // FETCH PREDICTION
  // -------------------------
  const fetchPrediction = useCallback(async () => {
    if (!selectedNode) return;

    setPredictionLoading(true);
    setPredictionError('');

    try {
      const response = await axios.get(
        'http://127.0.0.1:8000/api/v1/predictions-history'
      );

      const allPredictions = response.data || [];
      const actualNodeId = getActualTankId(selectedNode);

      const nodePredictions = allPredictions.filter(
        (item) => item.node_id === actualNodeId
      );

      if (nodePredictions.length > 0) {
        const sorted = nodePredictions.sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at)
        );

        const latest = sorted[0];
        setPrediction(latest.prediction);
        setConfidence(Math.round(latest.confidence * 100));
      } else {
        setPrediction(null);
        setConfidence(null);
        setPredictionError('No prediction data');
      }

    } catch (err) {
      console.error(err);
      setPredictionError('Prediction failed');
    } finally {
      setPredictionLoading(false);
    }
  }, [selectedNode]);

  // -------------------------
  // FETCH NODES
  // -------------------------
  const fetchNodes = useCallback(async () => {
    try {
      const res = await axios.get(config.TANK_PARAMETERS_URL);

      const transformed = (res.data || []).map(n => ({
        id: n.node_id,
        name: n.node_id,
        tank_height: n.tank_height_cm
      }));

      setNodes(transformed);

      if (transformed.length > 0 && !selectedNode) {
        setSelectedNode(transformed[0].id);
      }

    } catch (err) {
      console.error(err);
    }
  }, [selectedNode]);

  // -------------------------
  // EFFECTS
  // -------------------------
  useEffect(() => {
    fetchNodes();
  }, [fetchNodes]);

  useEffect(() => {
    if (selectedNode) {
      fetchSensorData();
      fetchPrediction();
    }
  }, [selectedNode, fetchSensorData, fetchPrediction]);

  // auto refresh
  useEffect(() => {
    const interval = setInterval(() => {
      fetchSensorData();
      fetchPrediction();
    }, 30000);

    return () => clearInterval(interval);
  }, [fetchSensorData, fetchPrediction]);

  // -------------------------
  // CHART DATA
  // -------------------------
  const confidencePieData = useMemo(() => {
    if (confidence === null) return [];
    return [
      { name: 'Confidence', value: confidence },
      { name: 'Remaining', value: 100 - confidence }
    ];
  }, [confidence]);

  // -------------------------
  // UI
  // -------------------------
  return (
    <div className="home-page">

      <h2>Dashboard</h2>

      <select
        value={selectedNode}
        onChange={(e) => setSelectedNode(e.target.value)}
      >
        {nodes.map(n => (
          <option key={n.id} value={n.id}>{n.id}</option>
        ))}
      </select>

      <h3>Water Level: {waterLevel}%</h3>
      <h3>Temperature: {temperature}°C</h3>

      {/* PREDICTION CARD */}
      <div>
        <h3>Prediction</h3>
        <p>{predictionLoading ? 'Loading...' : prediction}</p>
        <p>{confidence !== null ? `${confidence}% confidence` : ''}</p>
        {predictionError && <p>{predictionError}</p>}
      </div>

      {/* PIE */}
      {confidence !== null && (
        <ResponsiveContainer width="100%" height={200}>
          <PieChart>
            <Pie data={confidencePieData} dataKey="value">
              <Cell fill="#2196F3" />
              <Cell fill="#ddd" />
            </Pie>
          </PieChart>
        </ResponsiveContainer>
      )}

      {/* WATER GRAPH */}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={waterLevelData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip />
          <Line dataKey="value" stroke="#2196F3" />
        </LineChart>
      </ResponsiveContainer>

      {/* TEMP GRAPH */}
      <ResponsiveContainer width="100%" height={300}>
        <LineChart data={temperatureData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="time" />
          <YAxis />
          <Tooltip />
          <Line dataKey="value" stroke="#FF9800" />
        </LineChart>
      </ResponsiveContainer>

    </div>
  );
};

export default Home;
