import React, { useState } from 'react';
import { Sparkles, Play, CheckCircle, Database, Search, ShieldAlert, BarChart3, ChevronRight } from 'lucide-react';

function App() {
  const [pipelineRun, setPipelineRun] = useState(null);
  const [status, setStatus] = useState('idle'); // idle, running, completed
  const [activeTab, setActiveTab] = useState('reviews');

  const startPipeline = () => {
    setStatus('running');
    setPipelineRun({
      id: 'pipeline-run-' + Math.floor(Math.random() * 10000),
      phase: 'Ingesting data...',
      progress: 20
    });

    // Simulate phases in background
    setTimeout(() => {
      setPipelineRun(prev => ({ ...prev, phase: 'Cleaning reviews (Agent 2)...', progress: 40 }));
    }, 2000);

    setTimeout(() => {
      setPipelineRun(prev => ({ ...prev, phase: 'Running core thematic analyses (Agent 3 & 4)...', progress: 70 }));
    }, 4000);

    setTimeout(() => {
      setPipelineRun(prev => ({ ...prev, phase: 'Compiling product report (Agent 6 & 7)...', progress: 90 }));
    }, 6000);

    setTimeout(() => {
      setStatus('completed');
      setPipelineRun(prev => ({ ...prev, phase: 'Analysis completed successfully!', progress: 100 }));
    }, 8000);
  };

  return (
    <div style={{ maxWidth: '1200px', margin: '0 auto', padding: '40px 20px' }}>
      
      {/* Header */}
      <header style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '40px' }} className="animate-fade-in">
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Sparkles size={28} color="#6366f1" />
            <h1 style={{ margin: 0, fontSize: '28px', background: 'linear-gradient(90deg, #f8fafc, #6366f1)', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent' }}>
              Review Discovery Engine
            </h1>
          </div>
          <p style={{ color: '#94a3b8', margin: '4px 0 0 0' }}>Discovering music app user insights with Groq Multi-Agent system</p>
        </div>
        <div>
          <button onClick={startPipeline} disabled={status === 'running'} style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Play size={16} fill="white" />
            {status === 'running' ? 'Running Analysis...' : 'Run Pipeline'}
          </button>
        </div>
      </header>

      {/* Metrics Cards Grid */}
      <section style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(250px, 1fr))', gap: '20px', marginBottom: '40px' }}>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '12px' }}>
            <span>Total Reviews</span>
            <Database size={20} />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold' }}>1,248</div>
          <div style={{ fontSize: '12px', color: '#10b981', marginTop: '4px' }}>+12% vs last week</div>
        </div>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '12px' }}>
            <span>Discovery Issues Flagged</span>
            <ShieldAlert size={20} color="#f59e0b" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#f59e0b' }}>432</div>
          <div style={{ fontSize: '12px', color: '#94a3b8', marginTop: '4px' }}>34.6% of total reviews</div>
        </div>
        <div className="card">
          <div style={{ display: 'flex', justifyContent: 'space-between', color: '#94a3b8', marginBottom: '12px' }}>
            <span>Active Insights Agents</span>
            <Sparkles size={20} color="#ec4899" />
          </div>
          <div style={{ fontSize: '32px', fontWeight: 'bold', color: '#ec4899' }}>7 / 7</div>
          <div style={{ fontSize: '12px', color: '#10b981', marginTop: '4px' }}>All agents online</div>
        </div>
      </section>

      {/* Pipeline Status Banner */}
      {pipelineRun && (
        <section className="card animate-fade-in" style={{ marginBottom: '40px', borderLeft: '4px solid #6366f1' }}>
          <h3 style={{ marginBottom: '12px', display: 'flex', alignItems: 'center', gap: '8px' }}>
            {status === 'completed' ? <CheckCircle color="#10b981" size={18} /> : <Sparkles className="animate-spin" color="#6366f1" size={18} />}
            Pipeline Run: {pipelineRun.id}
          </h3>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '14px', color: '#94a3b8', marginBottom: '8px' }}>
            <span>Current Status: {pipelineRun.phase}</span>
            <span>{pipelineRun.progress}%</span>
          </div>
          <div className="progress-bar-container">
            <div className="progress-bar-fill" style={{ width: `${pipelineRun.progress}%` }}></div>
          </div>
        </section>
      )}

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '20px', borderBottom: '1px solid #1e293b', marginBottom: '30px' }}>
        <button 
          onClick={() => setActiveTab('reviews')} 
          style={{ background: 'none', borderBottom: activeTab === 'reviews' ? '2px solid #6366f1' : '2px solid transparent', color: activeTab === 'reviews' ? '#f8fafc' : '#64748b', padding: '12px 6px', borderRadius: 0, fontWeight: 'bold' }}>
          Analyzed Reviews
        </button>
        <button 
          onClick={() => setActiveTab('insights')} 
          style={{ background: 'none', borderBottom: activeTab === 'insights' ? '2px solid #6366f1' : '2px solid transparent', color: activeTab === 'insights' ? '#f8fafc' : '#64748b', padding: '12px 6px', borderRadius: 0, fontWeight: 'bold' }}>
          Product Discovery Answers
        </button>
      </div>

      {/* Tabs Content */}
      <main>
        {activeTab === 'reviews' ? (
          <div className="card animate-fade-in" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '20px', borderBottom: '1px solid #1e293b', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <h3 style={{ margin: 0 }}>Review Database</h3>
              <div style={{ display: 'flex', gap: '8px', background: '#12121e', padding: '6px 12px', borderRadius: '8px', border: '1px solid #1e293b' }}>
                <Search size={16} color="#64748b" />
                <input type="text" placeholder="Search reviews..." style={{ background: 'none', border: 'none', color: '#f8fafc', outline: 'none', fontSize: '13px' }} />
              </div>
            </div>
            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #1e293b', color: '#64748b', fontSize: '13px' }}>
                  <th style={{ padding: '16px 20px' }}>Review</th>
                  <th style={{ padding: '16px 20px' }}>Sentiment</th>
                  <th style={{ padding: '16px 20px' }}>Primary Theme</th>
                  <th style={{ padding: '16px 20px' }}>Rating</th>
                </tr>
              </thead>
              <tbody>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '16px 20px', maxWidth: '400px' }}>"The recommendations are so repetitive, playing the exact same track list every hour."</td>
                  <td style={{ padding: '16px 20px' }}><span style={{ padding: '4px 8px', borderRadius: '6px', fontSize: '11px', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>negative</span></td>
                  <td style={{ padding: '16px 20px', color: '#6366f1' }}>Recommendation Boredom</td>
                  <td style={{ padding: '16px 20px', color: '#f59e0b' }}>★★☆☆☆</td>
                </tr>
                <tr style={{ borderBottom: '1px solid #1e293b' }}>
                  <td style={{ padding: '16px 20px', maxWidth: '400px' }}>"Can't discover new music easily. The smart playlists just give me songs I already liked."</td>
                  <td style={{ padding: '16px 20px' }}><span style={{ padding: '4px 8px', borderRadius: '6px', fontSize: '11px', background: 'rgba(239, 68, 68, 0.1)', color: '#ef4444' }}>negative</span></td>
                  <td style={{ padding: '16px 20px', color: '#6366f1' }}>Discovery Friction</td>
                  <td style={{ padding: '16px 20px', color: '#f59e0b' }}>★☆☆☆☆</td>
                </tr>
                <tr>
                  <td style={{ padding: '16px 20px', maxWidth: '400px' }}>"Audio quality is superb and lossless stream is seamless."</td>
                  <td style={{ padding: '16px 20px' }}><span style={{ padding: '4px 8px', borderRadius: '6px', fontSize: '11px', background: 'rgba(16, 185, 129, 0.1)', color: '#10b981' }}>positive</span></td>
                  <td style={{ padding: '16px 20px', color: '#94a3b8' }}>Sound Quality</td>
                  <td style={{ padding: '16px 20px', color: '#f59e0b' }}>★★★★★</td>
                </tr>
              </tbody>
            </table>
          </div>
        ) : (
          <div style={{ display: 'grid', gap: '20px' }} className="animate-fade-in">
            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6366f1' }}>
                <ChevronRight size={18} /> Why do users struggle to discover new music?
              </h3>
              <p style={{ color: '#94a3b8', fontSize: '14px', marginLeft: '26px' }}>
                Users highlight that discovery algorithms prioritize safe, familiar tracks rather than introducing niche, novel recommendations, leading to a closed-loop selection fatigue.
              </p>
            </div>
            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6366f1' }}>
                <ChevronRight size={18} /> What are the biggest frustrations with music recommendations?
              </h3>
              <p style={{ color: '#94a3b8', fontSize: '14px', marginLeft: '26px' }}>
                Repeated recommendations of recently deleted tracks, static daily mix playlists that do not rotate weekly, and lack of fine-grained configuration sliders to change recommendation randomness levels.
              </p>
            </div>
            <div className="card">
              <h3 style={{ display: 'flex', alignItems: 'center', gap: '8px', color: '#6366f1' }}>
                <ChevronRight size={18} /> What causes users to repeatedly listen to the same songs?
              </h3>
              <p style={{ color: '#94a3b8', fontSize: '14px', marginLeft: '26px' }}>
                Inability to discover reliable search results and recommendations leads users to rely heavily on self-curated playlists of familiar comfort tracks.
              </p>
            </div>
          </div>
        )}
      </main>
    </div>
  );
}

export default App;
