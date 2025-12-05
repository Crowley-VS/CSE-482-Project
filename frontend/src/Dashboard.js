import React from 'react';
import './App.css';

function Dashboard() {
  return (
    <div className="dashboard-container">
      <div className="dashboard-content">
        <h1>Detected Event Clusters</h1>
        <div className="output-box">
          Output from backend
        </div>
      </div>
    </div>
  );
}

export default Dashboard;
