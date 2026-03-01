import React, { useEffect, useState } from 'react';
import './App.css';

function Dashboard({ navigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let mounted = true;

    const fetchEvents = async () => {
      try {
        setLoading(true);
        // Determine which URL to call:
        // - If REACT_APP_API_BASE is set at build time, use it.
        // - If running on localhost (dev), use the relative proxy path so CRA dev server proxies to production.
        // - Otherwise (deployed static site), call the full production URL.
        const envBase = process.env.REACT_APP_API_BASE;
        const fetchUrl = envBase
          ? `${envBase.replace(/\/$/, '')}/api/v1/events/`
          : (window.location.hostname === 'localhost'
            ? '/api/v1/events/'
            : 'https://cse-482-project-production.up.railway.app/api/v1/events/');

        console.debug('Fetching events from', fetchUrl);
        const response = await fetch(fetchUrl);
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
        <h1>Economic Event Detection from Reddit and Twitter</h1>

        {loading && <div className="output-box">Loading…</div>}
        {error && <div className="output-box">Error: {error}</div>}

        {!loading && !error && (
          <div className="events-grid">
            {(data && data.events && data.events.length > 0) ? (
              data.events.map((ev) => (
                <div key={ev.id} className="event-card">
                  <div className="event-header">
                    <div className="event-id">ID: {ev.id}</div>
                    <div className="event-name">{ev.event_name ?? ev.event_name}</div>
                  </div>
                  <div className="event-desc">{ev.description ?? ev.summary?.summary_text ?? ''}</div>
                  <div className="event-actions">
                    <button className="view-btn" onClick={() => navigate(`/events/${ev.id}`)}>View Details</button>
                  </div>
                </div>
              ))
            ) : (
              <div className="no-events">No events detected.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default Dashboard;
