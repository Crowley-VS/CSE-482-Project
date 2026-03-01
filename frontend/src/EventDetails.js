import React, { useEffect, useState } from 'react';
import './App.css';

function resolveFetchUrl(path) {
  const envBase = process.env.REACT_APP_API_BASE;
  if (envBase) return `${envBase.replace(/\/$/, '')}${path}`;
  if (window.location.hostname === 'localhost') return path; // proxy in dev
  return `https://cse-482-project-production.up.railway.app${path}`;
}


export default function EventDetails({ eventId, navigate }) {
  const [postsData, setPostsData] = useState(null);
  const [eventData, setEventData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!eventId) return;
    let mounted = true;

    const fetchAll = async () => {
      try {
        setLoading(true);
        // Fetch event details (for summary)
        const eventUrl = resolveFetchUrl(`/api/v1/events/${eventId}`);
        const postsUrl = resolveFetchUrl(`/api/v1/events/${eventId}/posts/`);
        const [eventRes, postsRes] = await Promise.all([
          fetch(eventUrl),
          fetch(postsUrl)
        ]);
        if (!eventRes.ok) throw new Error(`Event fetch error: ${eventRes.status}`);
        if (!postsRes.ok) throw new Error(`Posts fetch error: ${postsRes.status}`);
        const eventJson = await eventRes.json();
        const postsJson = await postsRes.json();
        if (!mounted) return;
        setEventData(eventJson);
        setPostsData(postsJson);
        setError(null);
      } catch (err) {
        if (!mounted) return;
        setError(err instanceof Error ? err.message : 'Failed to fetch event/posts');
        setEventData(null);
        setPostsData(null);
      } finally {
        if (!mounted) return;
        setLoading(false);
      }
    };

    fetchAll();
    return () => { mounted = false; };
  }, [eventId]);

  let summaryText = '';
  if (eventData && eventData.summary && eventData.summary.summary_text) {
    summaryText = eventData.summary.summary_text;
  }

  // Format keywords for heading, capitalized and on new line
  let keywordsLine = null;
  if (eventData && Array.isArray(eventData.keywords) && eventData.keywords.length > 0) {
    const capWords = eventData.keywords.map(w => w.charAt(0).toUpperCase() + w.slice(1));
    keywordsLine = <div style={{fontSize: '1.1em', margin: '8px 0 16px 0', fontWeight: 500}}><strong>(
      {capWords.join(', ')}
    )</strong></div>;
  }

  return (
    <div className="dashboard-container">
      <div className="dashboard-content">
        <h1>Event {eventId} Associated Posts:</h1>
        {keywordsLine}
        {summaryText && (
          <div className="output-box" style={{ marginBottom: 16, background: '#e3f0ff', color: '#1a237e', fontWeight: 500 }}>
            <strong>Summary:</strong> {summaryText}
          </div>
        )}
        <div style={{ marginBottom: 12 }}>
          <button className="back-btn" onClick={() => navigate('/')}>Back to events</button>
        </div>

        {loading && <div className="output-box">Loading…</div>}
        {error && <div className="output-box">Error: {error}</div>}
        {!loading && !error && (
          <div className="posts-list">
            {postsData && postsData.posts && postsData.posts.length > 0 ? (
              postsData.posts.map((p) => (
                <article key={p.id} className="post-card">
                  <h2 className="post-title">{p.title || (p.text ? p.text.slice(0, 80) + '…' : `Post ${p.id}`)}</h2>
                  <div className="post-meta">
                    <span>{p.source}</span>
                    {p.subreddit && <span> • r/{p.subreddit}</span>}
                    {p.author && <span> • {p.author}</span>}
                    {typeof p.score !== 'undefined' && <span> • ▲ {p.score}</span>}
                  </div>
                  <div className="post-body">{p.text || ''}</div>
                  {p.url && <div className="post-link"><a href={p.url} target="_blank" rel="noopener noreferrer">Open original</a></div>}
                </article>
              ))
            ) : (
              <div className="output-box">No posts found for this event.</div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
