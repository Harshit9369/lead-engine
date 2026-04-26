import React, { useState, useEffect } from 'react';
import { schedulerAPI, leadsAPI, statsAPI, searchAPI, authAPI } from './api';
import { AuthProvider, useAuth } from './context/AuthContext';
import Auth from './pages/Auth';

const Dashboard = () => {
  const { user, logout, isAuthenticated } = useAuth();
  const [activeTab, setActiveTab] = useState('search'); // search, scans, saved, roles, profile
  const [stats, setStats] = useState({});
  const [roles, setRoles] = useState([]);
  const [groupedResults, setGroupedResults] = useState([]);
  const [savedLeads, setSavedLeads] = useState([]);
  const [loading, setLoading] = useState(false);
  const [showAuth, setShowAuth] = useState(false);

  // Search tab state
  const [searchTerm, setSearchTerm] = useState('');
  const [location, setLocation] = useState('India');
  const [searchResults, setSearchResults] = useState([]);
  const [searchStatus, setSearchStatus] = useState(null);

  // Profile state
  const [scanTime, setScanTime] = useState('10:00');

  // Toast state
  const [toast, setToast] = useState(null);

  const showToast = (message, type = 'success') => {
    setToast({ message, type });
    setTimeout(() => setToast(null), 3000);
  };

  useEffect(() => {
    if (isAuthenticated) {
      fetchStats();
      if (activeTab === 'scans') fetchGroupedResults();
      if (activeTab === 'saved') fetchSavedLeads();
      if (activeTab === 'roles') fetchRoles();
      if (activeTab === 'profile') fetchUserData();
    }
  }, [isAuthenticated, activeTab]);

  const fetchUserData = async () => {
    try {
      const res = await authAPI.getMe();
      setScanTime(res.data.preferred_scan_time || '10:00');
    } catch (err) {}
  };

  const fetchStats = async () => {
    try {
      const res = await statsAPI.get();
      setStats(res.data);
    } catch (err) {}
  };

  const fetchRoles = async () => {
    setLoading(true);
    try {
      const res = await schedulerAPI.listRoles();
      setRoles(res.data.roles);
    } catch (err) {}
    setLoading(false);
  };

  const fetchGroupedResults = async () => {
    setLoading(true);
    try {
      const res = await schedulerAPI.getGroupedResults();
      setGroupedResults(res.data.groups);
    } catch (err) {}
    setLoading(false);
  };

  const fetchSavedLeads = async () => {
    setLoading(true);
    try {
      const res = await leadsAPI.list();
      setSavedLeads(res.data.leads);
    } catch (err) {}
    setLoading(false);
  };

  const handleAddRole = async (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    const data = {
      role_keyword: formData.get('role_keyword'),
      location: formData.get('location'),
      industry: formData.get('industry'),
    };
    try {
      await schedulerAPI.addRole(data);
      e.target.reset();
      fetchRoles();
      fetchStats();
      showToast('Role added to schedule');
    } catch (err) { showToast('Error adding role', 'error'); }
  };

  const handleTriggerSearch = async () => {
    setLoading(true);
    setSearchResults([]);
    setSearchStatus(null);
    try {
      await searchAPI.trigger({ search_term: searchTerm, location });
      pollSearchStatus();
    } catch (err) { 
      setLoading(false);
      showToast('Search failed to start', 'error');
    }
  };

  const pollSearchStatus = async () => {
    const interval = setInterval(async () => {
      try {
        const res = await searchAPI.getStatus();
        setSearchStatus(res.data);
        if (!res.data.running) {
          clearInterval(interval);
          const results = await searchAPI.getResults();
          // Client-side deduplication as an extra safeguard
          const uniqueLeads = Array.from(new Map(results.data.leads.map(l => [l.job_url, l])).values());
          setSearchResults(uniqueLeads || []);
          setLoading(false);
        }
      } catch (err) {
        clearInterval(interval);
        setLoading(false);
      }
    }, 2000);
  };

  const handleTrackLead = async (resultId) => {
    if (!isAuthenticated) {
      setShowAuth(true);
      return;
    }
    try {
      await schedulerAPI.trackResult(resultId);
      fetchGroupedResults();
      fetchStats();
      showToast('Lead tracked successfully!');
    } catch (err) { showToast('Error tracking lead', 'error'); }
  };

  const handleSaveSearchResult = async (lead) => {
    if (!isAuthenticated) {
      setShowAuth(true);
      return;
    }
    try {
      await leadsAPI.save(lead);
      showToast('Lead saved successfully!', 'success');
      // Update local state to show "Saved" immediately
      setSearchResults(prev => prev.map(l => l.job_url === lead.job_url ? { ...l, is_saved: true } : l));
      fetchStats();
    } catch (err) { showToast('Error saving lead', 'error'); }
  };

  const handleUpdateScanTime = async (e) => {
    e.preventDefault();
    try {
      await authAPI.updateProfile({ preferred_scan_time: scanTime });
      showToast('Scan time updated!');
    } catch (err) { showToast('Error updating scan time', 'error'); }
  };

  if (showAuth && !isAuthenticated) {
    return (
      <div className="container">
        <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '2rem', padding: '1rem 0' }}>
          <h1 style={{ margin: 0, fontSize: '2.5rem', background: 'linear-gradient(to right, #6366f1, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Lead Engine
          </h1>
          <button className="btn btn-outline" onClick={() => setShowAuth(false)}>Back to Search</button>
        </header>
        <Auth onAuthComplete={() => setShowAuth(false)} />
      </div>
    );
  }

  return (
    <div className="container animate-fade-in">
      <header style={{ marginBottom: '3rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '2rem' }}>
        <div>
          <h1 style={{ margin: 0, fontSize: '2.5rem', background: 'linear-gradient(to right, #6366f1, #a855f7)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
            Lead Engine
          </h1>
          <p style={{ color: 'var(--text-muted)', margin: '0.5rem 0 0' }}>Automated Executive Hiring Intelligence</p>
        </div>
        <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
          {isAuthenticated && (
            <>
              <StatCard label="Leads" value={stats.total_saved_leads || 0} />
              <div style={{ textAlign: 'right' }}>
                <div style={{ fontSize: '0.9rem', fontWeight: 600 }}>{user.email.split('@')[0]}</div>
                <button onClick={logout} style={{ background: 'none', border: 'none', color: 'var(--danger)', cursor: 'pointer', fontSize: '0.8rem', padding: 0 }}>Logout</button>
              </div>
            </>
          )}
          {!isAuthenticated && (
            <button className="btn btn-primary" onClick={() => setShowAuth(true)}>Login / Sign Up</button>
          )}
        </div>
      </header>

      <nav className="glass" style={{ borderRadius: '1rem', padding: '0.5rem', display: 'flex', gap: '0.5rem', marginBottom: '2rem' }}>
        <TabButton active={activeTab === 'search'} onClick={() => setActiveTab('search')}>Instant Search</TabButton>
        <TabButton active={activeTab === 'scans'} onClick={() => {
          if (!isAuthenticated) setShowAuth(true); else setActiveTab('scans');
        }}>Daily Scans</TabButton>
        <TabButton active={activeTab === 'saved'} onClick={() => {
          if (!isAuthenticated) setShowAuth(true); else setActiveTab('saved');
        }}>Tracked Leads</TabButton>
        <TabButton active={activeTab === 'roles'} onClick={() => {
          if (!isAuthenticated) setShowAuth(true); else setActiveTab('roles');
        }}>Role Schedule</TabButton>
        {isAuthenticated && (
          <TabButton active={activeTab === 'profile'} onClick={() => setActiveTab('profile')}>Settings</TabButton>
        )}
      </nav>

      <main>
        {activeTab === 'search' && (
          <div className="animate-fade-in">
            <div className="card" style={{ marginBottom: '2rem', display: 'flex', gap: '1rem', alignItems: 'flex-end' }}>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Role Title</label>
                <input className="input" placeholder="e.g. Chief Financial Officer" value={searchTerm} onChange={e => setSearchTerm(e.target.value)} />
              </div>
              <div style={{ flex: 1 }}>
                <label style={{ display: 'block', marginBottom: '0.5rem', fontWeight: 600 }}>Location</label>
                <input className="input" placeholder="e.g. Bangalore, India" value={location} onChange={e => setLocation(e.target.value)} />
              </div>
              <button className="btn btn-primary" onClick={handleTriggerSearch} disabled={loading || !searchTerm}>
                {loading ? 'Searching...' : 'Scan Now'}
              </button>
            </div>

            {loading && (
              <div style={{ textAlign: 'center', padding: '3rem' }}>
                <div className="loader" style={{ marginBottom: '1rem' }}></div>
                <h3>Agent is crawling web sources...</h3>
              </div>
            )}

            {!loading && searchResults.length > 0 && (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
                {searchResults.map((lead, idx) => (
                  <LeadCard key={idx} lead={lead} onTrack={() => handleSaveSearchResult(lead)} />
                ))}
              </div>
            )}

            {!loading && searchResults.length === 0 && searchStatus && !searchStatus.running && (
              <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
                <h3>No leads found for "{searchTerm}"</h3>
              </div>
            )}
          </div>
        )}

        {isAuthenticated && activeTab === 'scans' && (
          <div className="animate-fade-in">
             <button className="btn btn-outline" style={{ marginBottom: '1rem' }} onClick={fetchGroupedResults} disabled={loading}>
               {loading ? <span className="loader" style={{ width: '12px', height: '12px', marginRight: '8px', borderThickness: '2px' }}></span> : '↻'} Refresh Results
             </button>
            {groupedResults.length === 0 ? (
              <div className="card" style={{ textAlign: 'center', padding: '4rem' }}>
                <h3>No daily scans found yet.</h3>
              </div>
            ) : (
              groupedResults.map(group => (
                <div key={group.role.id} style={{ marginBottom: '3rem' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1rem' }}>
                    <h2 style={{ margin: 0 }}>{group.role.role_keyword}</h2>
                    <span className="tag">{group.role.location || 'Remote'}</span>
                    <span style={{ color: 'var(--text-muted)', fontSize: '0.9rem' }}>{group.total} leads found</span>
                  </div>
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
                    {group.results.map(lead => (
                      <LeadCard key={lead.id} lead={lead} onTrack={() => handleTrackLead(lead.id)} isTracked={lead.is_saved} />
                    ))}
                  </div>
                </div>
              ))
            )}
          </div>
        )}

        {isAuthenticated && activeTab === 'saved' && (
          <div className="animate-fade-in">
             <button className="btn btn-outline" style={{ marginBottom: '1rem' }} onClick={fetchSavedLeads} disabled={loading}>
               {loading ? <span className="loader" style={{ width: '12px', height: '12px', marginRight: '8px' }}></span> : '↻'} Refresh Leads
             </button>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(350px, 1fr))', gap: '1.5rem' }}>
              {savedLeads.map(lead => (
                <LeadCard key={lead.id} lead={lead} showNotes />
              ))}
              {savedLeads.length === 0 && (
                <div className="card" style={{ gridColumn: '1 / -1', textAlign: 'center', padding: '4rem' }}>
                  <h3>You haven't tracked any leads yet.</h3>
                </div>
              )}
            </div>
          </div>
        )}

        {isAuthenticated && activeTab === 'roles' && (
          <div className="animate-fade-in grid-layout">
            <aside>
              <div className="card glass">
                <h3>Add Role</h3>
                <form onSubmit={handleAddRole}>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Keyword</label>
                    <input name="role_keyword" className="input" placeholder="e.g. CTO" required />
                  </div>
                  <div style={{ marginBottom: '1rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Location</label>
                    <input name="location" className="input" placeholder="India" />
                  </div>
                  <div style={{ marginBottom: '1.5rem' }}>
                    <label style={{ display: 'block', marginBottom: '0.5rem', fontSize: '0.9rem' }}>Industry</label>
                    <input name="industry" className="input" placeholder="Automotive" />
                  </div>
                  <button type="submit" className="btn btn-primary" style={{ width: '100%' }}>Add to Daily Scan</button>
                </form>
              </div>
            </aside>
            <section>
              <div className="card">
                <h3>Scanning Schedule</h3>
                <p className="text-muted" style={{ marginBottom: '1.5rem' }}>Scanned daily at {scanTime} IST.</p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
                   <button className="btn btn-outline" style={{ alignSelf: 'flex-start' }} onClick={fetchRoles}>Refresh Roles</button>
                  {roles.map(role => (
                    <div key={role.id} className="card glass" style={{ padding: '1rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <h4 style={{ margin: 0 }}>{role.role_keyword}</h4>
                        <span className="text-muted" style={{ fontSize: '0.8rem' }}>{role.location || 'Global'}</span>
                      </div>
                      <div style={{ display: 'flex', gap: '0.5rem' }}>
                        <button className="btn btn-outline" onClick={() => schedulerAPI.triggerScan(role.id)}>Run Now</button>
                        <button className="btn btn-outline" style={{ color: 'var(--danger)' }} onClick={async () => { await schedulerAPI.deleteRole(role.id); fetchRoles(); }}>Delete</button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </section>
          </div>
        )}

        {isAuthenticated && activeTab === 'profile' && (
          <div className="animate-fade-in card glass" style={{ maxWidth: '500px', margin: '0 auto' }}>
            <h3>Account Settings</h3>
            <form onSubmit={handleUpdateScanTime}>
              <div style={{ marginBottom: '1.5rem' }}>
                <label style={{ display: 'block', marginBottom: '0.5rem' }}>Preferred Daily Scan Time (IST)</label>
                <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
                  <input 
                    type="time" 
                    className="input" 
                    value={scanTime} 
                    onChange={(e) => setScanTime(e.target.value)} 
                  />
                  <button type="submit" className="btn btn-primary">Save</button>
                </div>
                <p className="text-muted" style={{ fontSize: '0.8rem', marginTop: '0.5rem' }}>The engine will automatically scan all your active roles at this time every day.</p>
              </div>
            </form>
          </div>
        )}
      </main>

      {toast && (
        <div className="glass animate-fade-in" style={{
          position: 'fixed',
          bottom: '2rem',
          right: '2rem',
          padding: '1rem 2rem',
          borderRadius: '1rem',
          backgroundColor: toast.type === 'error' ? 'rgba(239, 68, 68, 0.95)' : 'rgba(34, 197, 94, 0.95)',
          color: 'white',
          fontWeight: 600,
          boxShadow: '0 10px 40px rgba(0,0,0,0.4)',
          zIndex: 1000,
          border: '1px solid rgba(255,255,255,0.2)',
          display: 'flex',
          alignItems: 'center',
          gap: '0.75rem'
        }}>
          <span>{toast.type === 'error' ? '❌' : '✅'}</span>
          {toast.message}
        </div>
      )}
    </div>
  );
};

const App = () => (
  <AuthProvider>
    <Dashboard />
  </AuthProvider>
);

const StatCard = ({ label, value }) => (
  <div className="card glass" style={{ padding: '0.5rem 1rem', textAlign: 'center' }}>
    <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase' }}>{label}</div>
    <div style={{ fontSize: '1.2rem', fontWeight: 800, color: 'var(--primary)' }}>{value}</div>
  </div>
);

const TabButton = ({ active, children, onClick }) => (
  <button onClick={onClick} className={`btn ${active ? 'btn-primary' : 'btn-outline'}`} style={{ flex: 1, justifyContent: 'center' }}>
    {children}
  </button>
);

const LeadCard = ({ lead, onTrack, isTracked, showNotes }) => {
  const { isAuthenticated } = useAuth();
  const copyLink = () => {
    navigator.clipboard.writeText(lead.job_url);
    alert('Link copied!');
  };

  return (
    <div className="card glass animate-fade-in" style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div>
          <div style={{ fontSize: '0.75rem', color: 'var(--primary)', fontWeight: 600 }}>{lead.source.toUpperCase()}</div>
          <h3 style={{ margin: 0, fontSize: '1.1rem' }}>{lead.job_title}</h3>
          <div style={{ color: 'var(--text-muted)', fontSize: '0.85rem' }}>{lead.company_name}</div>
        </div>
      </div>
      
      <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>📍 {lead.location || 'N/A'} • {lead.date_posted || 'Recent'}</div>

      <p style={{ fontSize: '0.85rem', margin: 0, display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', opacity: 0.8 }}>
        {lead.description || 'No description available.'}
      </p>

      <div style={{ marginTop: 'auto', display: 'flex', gap: '0.5rem' }}>
        <a href={lead.job_url} target="_blank" className="btn btn-primary" style={{ flex: 1, textDecoration: 'none', justifyContent: 'center', fontSize: '0.8rem' }}>Apply</a>
        <button className="btn btn-outline" onClick={copyLink}>🔗</button>
        {!isTracked && (
          <button className="btn btn-outline" onClick={onTrack} style={{ flex: 1.5, justifyContent: 'center', fontSize: '0.8rem' }}>
            {isAuthenticated ? 'Save' : 'Login to Save'}
          </button>
        )}
        {isTracked && (
          <button className="btn btn-outline" disabled style={{ flex: 1.5, justifyContent: 'center', opacity: 0.5, fontSize: '0.8rem' }}>Saved ✓</button>
        )}
      </div>
    </div>
  );
};

export default App;
