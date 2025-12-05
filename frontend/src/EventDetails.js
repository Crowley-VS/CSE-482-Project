import React, { useEffect, useState } from 'react';
import './App.css';

function resolveFetchUrl(path) {
  const envBase = process.env.REACT_APP_API_BASE;
  if (envBase) return `${envBase.replace(/\/$/, '')}${path}`;
  if (window.location.hostname === 'localhost') return path; // proxy in dev
  return `https://cse-482-project-production.up.railway.app${path}`;
}

export default function EventDetails({ eventId, navigate }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!eventId) return;
    let mounted = true;

    const fetchPosts = async () => {
      try {
        setLoading(true);
        const url = resolveFetchUrl(`/api/v1/events/${eventId}/posts/`);
        console.debug('Fetching event posts from', url);
        const res = await fetch(url);
        if (!res.ok) throw new Error(`HTTP error! status: ${res.status}`);
        const json = await res.json();
        if (!mounted) return;
        setData(json);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'Failed to fetch event posts');
        setData(null);
      } finally {
        if (!mounted) return;
        setLoading(false);
      }
    };

    fetchPosts();
    return () => { mounted = false; };
  }, [eventId]);

  return (
    <div className="dashboard-container">
      <div className="dashboard-content">
        <h1>Event {eventId} Associated Posts</h1>
        <div style={{ marginBottom: 12 }}>
          <button className="back-btn" onClick={() => navigate('/')}>Back to events</button>
        </div>

        {loading && <div className="output-box">Loading…</div>}
        {error && <div className="output-box">Error: {error}</div>}
        {!loading && !error && (
          <pre className="output-box">{JSON.stringify(data, null, 2)}</pre>
        )}
      </div>
    </div>
  );
}
