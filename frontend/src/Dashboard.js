import React, { useEffect, useState } from 'react';
import './App.css';

function Dashboard() {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const fetchEvents = async () => {
      try {
        setLoading(true);
        const response = await fetch(`/api/v1/events/`);
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const json = await response.json();
        if (!mounted) return;
        setData(json);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'Failed to fetch events');
        setData(null);
      } finally {
        if (!mounted) return;
        setLoading(false);
      }
    };

    fetchEvents();

    return () => {
      mounted = false;
    };
  }, []);

  return (
    <div className="dashboard-container">
      <div className="dashboard-content">
        <h1>Detected Event Clusters</h1>

        {loading && <div className="output-box">Loading…</div>}
        {error && <div className="output-box">Error: {error}</div>}

        {!loading && !error && (
          <pre className="output-box">{JSON.stringify(data, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
