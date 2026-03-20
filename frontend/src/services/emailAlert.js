class AnomalyDetector {
  constructor(thresholds = {}) {
    this.thresholds = {
      temperatureHigh: thresholds.temperatureHigh || 35,
      temperatureLow: thresholds.temperatureLow || 0,
      distanceHigh: thresholds.distanceHigh || 100,
      confidenceLow: thresholds.confidenceLow || 0.5,
      ...thresholds
    };
    
    this.anomalyHistory = [];
  }

  detectAnomalies(prediction) {
    const anomalies = [];

    if (prediction.temperature > this.thresholds.temperatureHigh) {
      anomalies.push({
        type: 'TEMPERATURE_HIGH',
        value: prediction.temperature,
        threshold: this.thresholds.temperatureHigh,
        severity: 'high'
      });
    }

    if (prediction.temperature < this.thresholds.temperatureLow) {
      anomalies.push({
        type: 'TEMPERATURE_LOW',
        value: prediction.temperature,
        threshold: this.thresholds.temperatureLow,
        severity: 'high'
      });
    }

    if (prediction.distance > this.thresholds.distanceHigh) {
      anomalies.push({
        type: 'DISTANCE_HIGH',
        value: prediction.distance,
        threshold: this.thresholds.distanceHigh,
        severity: 'medium'
      });
    }

    if (prediction.confidence < this.thresholds.confidenceLow) {
      anomalies.push({
        type: 'LOW_CONFIDENCE',
        value: prediction.confidence,
        threshold: this.thresholds.confidenceLow,
        severity: 'medium'
      });
    }

    if (anomalies.length > 0) {
      this.anomalyHistory.push({
        timestamp: new Date(),
        prediction,
        anomalies
      });
    }

    return anomalies;
  }

  async sendEmailAlert(anomalies, userEmail) {
    try {
      const response = await fetch('http://localhost:8000/api/v1/send-alert', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${localStorage.getItem('token')}`
        },
        body: JSON.stringify({
          email: userEmail,
          anomalies,
          timestamp: new Date().toISOString()
        })
      });

      return await response.json();
    } catch (error) {
      console.error('Error sending alert:', error);
      throw error;
    }
  }

  getAnomalyHistory() {
    return this.anomalyHistory;
  }

  clearHistory() {
    this.anomalyHistory = [];
  }
}

export default AnomalyDetector;