import { useState, useEffect } from 'react';
import ScoutNet from './components/ScoutNet';
import { getSiteData, type SiteData } from './siteDetection';
import './styles/ScoutNet.css';

function App() {
  const [siteData, setSiteData] = useState<SiteData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const chrom = (typeof globalThis !== 'undefined' && (globalThis as unknown as { chrome?: { tabs?: unknown } }).chrome) as
      | { tabs: { query: (q: object, cb: (tabs: { url?: string }[]) => void) => void } }
      | undefined;
    if (!chrom?.tabs) {
      setLoading(false);
      return;
    }
    chrom.tabs.query({ active: true, currentWindow: true }, (tabs: { url?: string }[]) => {
      const url = tabs[0]?.url;
      if (url && (url.startsWith('http:') || url.startsWith('https:'))) {
        getSiteData(url).then((data) => {
          setSiteData(data);
          setLoading(false);
        });
      } else {
        setLoading(false);
      }
    });
  }, []);

  if (loading) {
    return (
      <div className="app" style={{ padding: 24, textAlign: 'center', minWidth: 320 }}>
        <p style={{ color: '#64748B' }}>Checking this site...</p>
      </div>
    );
  }

  return (
    <div className="app" style={{ minWidth: 320 }}>
      <ScoutNet siteData={siteData ?? undefined} />
    </div>
  );
}

export default App;