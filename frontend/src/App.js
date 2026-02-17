import React, { useEffect, useState, useCallback } from 'react';
import './App.css';
import Dashboard from './Dashboard';
import EventDetails from './EventDetails';

function App() {
  const [path, setPath] = useState(window.location.pathname);

  useEffect(() => {
    const onPop = () => setPath(window.location.pathname);
    window.addEventListener('popstate', onPop);
    return () => window.removeEventListener('popstate', onPop);
  }, []);

  const navigate = useCallback((to) => {
    if (to === path) return;
    window.history.pushState({}, '', to);
    setPath(to);
  }, [path]);

  // simple routing: / -> dashboard, /events/:id -> details
  if (path.startsWith('/events/')) {
    const parts = path.split('/');
    const id = parts[2] || null;
    return <EventDetails eventId={id} navigate={navigate} />;
  }

  return (
    <div className="App">
      <Dashboard navigate={navigate} />
    </div>
  );
}

export default App;
