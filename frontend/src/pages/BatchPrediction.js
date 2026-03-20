import React, { useState } from 'react';
import './BatchPrediction.css';

const BatchPrediction = () => {
  const [file, setFile] = useState(null);
  const [predictions, setPredictions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [progress, setProgress] = useState(0);

  const handleFileSelect = (event) => {
    setFile(event.target.files[0]);
  };

  const handleUpload = async () => {
    if (!file) {
      alert('Please select a file');
      return;
    }

    setLoading(true);
    const formData = new FormData();
    formData.append('file', file);

    try {
      const response = await fetch('http://localhost:8000/api/v1/batch-predict', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: formData
      });

      const data = await response.json();
      
      if (data.predictions) {
        setPredictions(data.predictions);
        setProgress(100);
      }
    } catch (error) {
      console.error('Upload error:', error);
      alert('Error uploading file');
    } finally {
      setLoading(false);
    }
  };

  const downloadResults = () => {
    const csv = [
      ['Distance', 'Temperature', 'Prediction', 'Confidence'],
      ...predictions.map(p => [
        p.distance,
        p.temperature,
        p.prediction,
        (p.confidence * 100).toFixed(2) + '%'
      ])
    ]
    .map(row => row.join(','))
    .join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'predictions.csv';
    a.click();
  };

  return (
    <div className="batch-prediction">
      <div className="upload-section">
        <h2>Batch Prediction Upload</h2>
        <p>Upload a CSV file with columns: distance, temperature</p>

        <div className="file-input-wrapper">
          <input
            type="file"
            accept=".csv"
            onChange={handleFileSelect}
            disabled={loading}
          />
          <label>{file ? file.name : 'Choose CSV file...'}</label>
        </div>

        <button
          className="btn-upload"
          onClick={handleUpload}
          disabled={loading || !file}
        >
          {loading ? 'Uploading...' : 'Upload & Predict'}
        </button>

        {loading && (
          <div className="progress-bar">
            <div className="progress-fill" style={{ width: `${progress}%` }}></div>
          </div>
        )}
      </div>

      {predictions.length > 0 && (
        <div className="results-section">
          <div className="results-header">
            <h3>Predictions ({predictions.length})</h3>
            <button className="btn-download" onClick={downloadResults}>
              📥 Download Results
            </button>
          </div>

          <div className="results-table">
            <table>
              <thead>
                <tr>
                  <th>Distance</th>
                  <th>Temperature</th>
                  <th>Prediction</th>
                  <th>Confidence</th>
                </tr>
              </thead>
              <tbody>
                {predictions.map((pred, idx) => (
                  <tr key={idx}>
                    <td>{pred.distance}</td>
                    <td>{pred.temperature}</td>
                    <td><strong>{pred.prediction}</strong></td>
                    <td>
                      <div className="confidence-bar">
                        <div
                          className="confidence-fill"
                          style={{ width: `${pred.confidence * 100}%` }}
                        ></div>
                        <span>{(pred.confidence * 100).toFixed(1)}%</span>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
};

export default BatchPrediction;