import React, { useState, useEffect, useMemo } from 'react';
import {
  LineChart, Line, BarChart, Bar, PieChart, Pie, Cell,
  XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend,
} from 'recharts';
import axios from 'axios';
import config from '../config';

const Home = () => {
  const [waterLevel, setWaterLevel] = useState(0);
  const [temperature, setTemperature] = useState(0);
  const [waterLevelData, setWaterLevelData] = useState([]);
  const [temperatureData, setTemperatureData] = useState([]);
  const [loading, setLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState(null);
  const [nodes, setNodes] = useState([]);
  const [selectedNode, setSelectedNode] = useState('');
  const [hasDataForNode, setHasDataForNode] = useState(true);
  const [nodeDataMessage, setNodeDataMessage] = useState('');

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
  const fetchSensorData = async () => {
    try {
      setLoading(true);

      const response = await axios.get(config.SENSOR_DATA_URL);
      const allSensorData = response.data || [];

      const actualNodeId = getActualTankId(selectedNode);

      const sensorData = allSensorData.filter(
        (item) => item.node_id === actualNodeId
      );

      if (sensorData.length > 0) {
        setHasDataForNode(true);

        const latest = sensorData[0];

        const selectedNodeData = nodes.find(n => n.id === selectedNode);
        const tankHeight = selectedNodeData?.tank_height || 200;

        const waterLevelPercentage = Math.min(
          100,
          Math.round(((tankHeight - latest.distance) / tankHeight) * 100)
        );

        setWaterLevel(waterLevelPercentage);
        setTemperature(Math.round(latest.temperature * 10) / 10);
        setLastUpdated(new Date(latest.created_at));

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
        setHasDataForNode(false);
        setWaterLevel(0);
        setTemperature(0);
        setWaterLevelData([]);
        setTemperatureData([]);
      }

    } catch (error) {
      console.error(error);
      setHasDataForNode(false);
    } finally {
      setLoading(false);
    }
  };

  // -------------------------
  // ✅ NEW PREDICTION FETCH
  // -------------------------
  const fetchPrediction = async () => {
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

        // SORT latest first
        const sorted = nodePredictions.sort(
          (a, b) => new Date(b.created_at) - new Date(a.created_at)
        );

        const latest = sorted[0];

        setPrediction(latest.prediction);
        setConfidence(Math.round(latest.confidence * 100));
        setLastUpdated(new Date(latest.created_at));

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
  };

  // -------------------------
  // FETCH NODES
  // -------------------------
  const fetchNodes = async () => {
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
  };

  // -------------------------
  // EFFECTS
  // -------------------------
  useEffect(() => {
    fetchNodes();
  }, []);

  useEffect(() => {
    if (selectedNode) {
      fetchSensorData();
      fetchPrediction();
    }
  }, [selectedNode]);

  // auto refresh
  useEffect(() => {
    const interval = setInterval(() => {
      fetchSensorData();
      fetchPrediction();
    }, 30000);

    return () => clearInterval(interval);
  }, [selectedNode]);

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

      {/* ✅ PREDICTION CARD */}
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