import React, { useState, useEffect } from 'react';
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';
import './ModelComparison.css';

const ModelComparison = () => {
  const [modelInfo, setModelInfo] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetchModelInfo();
  }, []);

  const fetchModelInfo = async () => {
    try {
      const response = await fetch('http://localhost:8000/api/v1/model-info');
      const data = await response.json();
      setModelInfo(data);
      setLoading(false);
    } catch (error) {
      console.error('Error fetching model info:', error);
      setLoading(false);
    }
  };

  if (loading) {
    return <div className="loading">Loading model information...</div>;
  }

  if (!modelInfo) {
    return <div className="error">Failed to load model information</div>;
  }

  const comparisonData = Object.entries(modelInfo.all_models || {}).map(([name, metrics]) => ({
    name,
    accuracy: metrics.accuracy * 100,
    f1_score: metrics.f1_score * 100,
    precision: metrics.precision * 100,
    recall: metrics.recall * 100
  }));

  return (
    <div className="model-comparison">
      <h1>Model Comparison Analysis</h1>

      <div className="best-model-card">
        <h2>🏆 Best Model: {modelInfo.best_model}</h2>
        <div className="metrics-grid">
          <div className="metric">
            <span className="label">Accuracy</span>
            <span className="value">{(modelInfo.accuracy * 100).toFixed(2)}%</span>
          </div>
          <div className="metric">
            <span className="label">F1 Score</span>
            <span className="value">{(modelInfo.f1_score * 100).toFixed(2)}%</span>
          </div>
          <div className="metric">
            <span className="label">Classes</span>
            <span className="value">{modelInfo.num_classes}</span>
          </div>
        </div>
      </div>

      <div className="charts-container">
        <div className="chart">
          <h3>Accuracy Comparison</h3>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Bar dataKey="accuracy" fill="#8884d8" />
            </BarChart>
          </ResponsiveContainer>
        </div>

        <div className="chart">
          <h3>Metrics Comparison</h3>
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={comparisonData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="name" />
              <YAxis />
              <Tooltip />
              <Legend />
              <Line type="monotone" dataKey="accuracy" stroke="#8884d8" />
              <Line type="monotone" dataKey="f1_score" stroke="#82ca9d" />
              <Line type="monotone" dataKey="precision" stroke="#ffc658" />
              <Line type="monotone" dataKey="recall" stroke="#ff7c7c" />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      <div className="details-table">
        <h3>Detailed Metrics</h3>
        <table>
          <thead>
            <tr>
              <th>Model</th>
              <th>Accuracy</th>
              <th>F1 Score</th>
              <th>Precision</th>
              <th>Recall</th>
            </tr>
          </thead>
          <tbody>
            {comparisonData.map((row) => (
              <tr key={row.name} className={row.name === modelInfo.best_model ? 'best' : ''}>
                <td><strong>{row.name}</strong></td>
                <td>{row.accuracy.toFixed(2)}%</td>
                <td>{row.f1_score.toFixed(2)}%</td>
                <td>{row.precision.toFixed(2)}%</td>
                <td>{row.recall.toFixed(2)}%</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};

export default ModelComparison;