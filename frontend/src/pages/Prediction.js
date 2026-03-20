import React, { useEffect, useState } from 'react';
import axios from 'axios';
import {
  PieChart,
  Pie,
  Cell,
  ResponsiveContainer,
  Tooltip,
  Legend,
} from 'recharts';

const Prediction = () => {
  const [distance, setDistance] = useState('');
  const [temperature, setTemperature] = useState('');
  const [prediction, setPrediction] = useState(null);
  const [confidence, setConfidence] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [modelInfo, setModelInfo] = useState(null);

  useEffect(() => {
    const fetchModelInfo = async () => {
      try {
        const response = await axios.get('http://127.0.0.1:8000/api/v1/model-info');
        setModelInfo(response.data);
      } catch (err) {
        console.error('Error fetching model info:', err);
      }
    };

    fetchModelInfo();
  }, []);

  const handlePredict = async () => {
    setError('');
    setPrediction(null);
    setConfidence(null);

    const distNum = parseFloat(distance);
    const tempNum = parseFloat(temperature);

    if (Number.isNaN(distNum) || Number.isNaN(tempNum)) {
      setError('Please enter valid numeric values for distance and temperature.');
      return;
    }

    setLoading(true);

    try {
      const response = await axios.post('http://127.0.0.1:8000/predict', {
        distance: distNum,
        temperature: tempNum,
      });

      const data = response.data || {};
      setPrediction(data.prediction ?? null);
      setConfidence(
        typeof data.confidence === 'number' ? Math.round(data.confidence * 100) : null
      );
    } catch (err) {
      console.error('Prediction request failed:', err);
      setError('Prediction request failed. Please check the server and try again.');
    } finally {
      setLoading(false);
    }
  };

  const pieData = confidence !== null
    ? [
        { name: 'Confidence', value: confidence },
        { name: 'Remaining', value: 100 - confidence },
      ]
    : [];

  const pieColors = ['var(--color-primary)', 'rgba(0,0,0,0.08)'];

  return (
    <div className="home-page">
      <div className="page-header">
        <h1 className="page-title">Prediction</h1>
        {modelInfo && (
          <div style={{ fontSize: '0.9rem', color: 'var(--color-muted)' }}>
            Model: {modelInfo.name ?? modelInfo.model_name ?? 'Unknown'}
            {modelInfo.version ? ` (v${modelInfo.version})` : ''}
          </div>
        )}
      </div>

      <div style={{ maxWidth: 700, margin: '0 auto' }}>
        <div
          style={{
            padding: 20,
            borderRadius: 12,
            background: 'var(--color-surface)',
            boxShadow: 'var(--shadow)',
            marginBottom: 20,
          }}
        >
          <div style={{ display: 'grid', gap: 14 }}>
            <label style={{ fontWeight: 600, color: 'var(--color-text)' }}>
              Distance (cm)
              <input
                type="number"
                value={distance}
                onChange={(e) => setDistance(e.target.value)}
                placeholder="Enter distance"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  marginTop: 6,
                  borderRadius: 8,
                  border: '1px solid rgba(0,0,0,0.2)',
                }}
              />
            </label>

            <label style={{ fontWeight: 600, color: 'var(--color-text)' }}>
              Temperature (°C)
              <input
                type="number"
                value={temperature}
                onChange={(e) => setTemperature(e.target.value)}
                placeholder="Enter temperature"
                style={{
                  width: '100%',
                  padding: '10px 12px',
                  marginTop: 6,
                  borderRadius: 8,
                  border: '1px solid rgba(0,0,0,0.2)',
                }}
              />
            </label>

            <button
              onClick={handlePredict}
              disabled={loading}
              style={{
                padding: '12px 18px',
                borderRadius: 10,
                border: 'none',
                background: 'var(--color-primary)',
                color: 'white',
                fontWeight: 600,
                cursor: loading ? 'not-allowed' : 'pointer',
              }}
            >
              {loading ? 'Predicting…' : 'Run Prediction'}
            </button>

            {error && (
              <div style={{ color: '#b91c1c', fontWeight: 600 }}>{error}</div>
            )}

            {prediction !== null && (
              <div
                style={{
                  padding: 16,
                  borderRadius: 10,
                  border: '1px solid rgba(0,0,0,0.12)',
                  background: 'var(--color-surface-2)',
                }}
              >
                <div style={{ marginBottom: 8 }}>
                  <strong>Prediction:</strong> {prediction}
                </div>
                {confidence !== null && (
                  <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
                    <div>
                      <div style={{ fontSize: '0.9rem', color: 'var(--color-muted)' }}>
                        Confidence
                      </div>
                      <div style={{ fontSize: '1.4rem', fontWeight: 700 }}>
                        {confidence}%
                      </div>
                    </div>

                    <div style={{ width: 140, height: 140 }}>
                      <ResponsiveContainer width="100%" height="100%">
                        <PieChart>
                          <Pie
                            data={pieData}
                            innerRadius={46}
                            outerRadius={62}
                            startAngle={90}
                            endAngle={-270}
                            dataKey="value"
                          >
                            {pieData.map((entry, index) => (
                              <Cell key={`cell-${index}`} fill={pieColors[index]} />
                            ))}
                          </Pie>
                          <Tooltip formatter={(value) => `${value}%`} />
                          <Legend verticalAlign="bottom" height={20} />
                        </PieChart>
                      </ResponsiveContainer>
                    </div>
                  </div>
                )}
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default Prediction;
