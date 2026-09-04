import { useEffect, useState } from 'react'
import MagneticFieldBackground from './components/MagneticFieldBackground'
import UploadBox from './components/UploadBox'
import AnalysisProgress from './components/AnalysisProgress'
import ResultDashboard from './components/ResultDashboard'
import { analysisStages, demoProfiles } from './data/analysisData'
import './App.css'

function App() {
  const [file, setFile] = useState(null); const [view, setView] = useState('landing'); const [stage, setStage] = useState(0); const [profile, setProfile] = useState('flagged')
  useEffect(() => { if (view !== 'progress') return; if (stage >= analysisStages.length) { const done = setTimeout(() => setView('results'), 350); return () => clearTimeout(done) }; const timer = setTimeout(() => setStage(s => s + 1), 480); return () => clearTimeout(timer) }, [view, stage])
  const startAnalysis = () => { setStage(0); setView('progress') }; const reset = () => { if (file?.url) URL.revokeObjectURL(file.url); setFile(null); setView('landing'); setStage(0) }
  if (view === 'progress') return <AnalysisProgress stage={stage} />
  if (view === 'results') return <ResultDashboard result={demoProfiles[profile]} file={file} onReset={reset} />
  return <div className="app"><MagneticFieldBackground /><header className="site-header"><a className="wordmark" href="#top">GLANCE</a><nav aria-label="Primary navigation"><a href="#product">Product</a><a href="#how-it-works">How it works</a><a href="#security">Security</a><a href="#about">About</a></nav><a className="header-cta" href="#product">Verify an image</a></header><main id="top"><section className="hero-section" id="product"><p className="eyebrow">EXPLAINABLE IDENTITY SECURITY</p><h1>A Single Glance<br />Verifies the Truth</h1><p className="hero-subtitle">Explainable AI-Powered KYC Deepfake Detection</p><p className="hero-copy">Analyze identity images for signs of AI generation, manipulation, and biometric inconsistencies — with explainable forensic signals instead of black-box decisions.</p><UploadBox file={file} onFile={setFile} onAnalyze={startAnalysis} demoProfile={profile} setDemoProfile={setProfile} /></section><section className="how-section" id="how-it-works"><p className="eyebrow">HOW IT WORKS</p><div className="section-heading"><h2>Clear evidence, before a decision.</h2><p>Glance organizes complex image signals into a calm, reviewable assessment.</p></div><div className="steps">{[['01','Upload','Upload an identity image.'],['02','Analyze','Glance examines biometric and forensic signals.'],['03','Explain','The system identifies suspicious patterns.'],['04','Verify','Review the risk assessment before making a decision.']].map(([num, title, copy]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{copy}</p></article>)}</div></section><section className="trust-section" id="security"><div><p className="eyebrow">TRUST, MADE MEASURABLE</p><h2>Security teams need more than a score.</h2><p>Glance brings AI-generation detection, biometric consistency, image forensics, metadata signals, and human-readable explanations into one considered review.</p></div><ul><li>AI-generation detection</li><li>Biometric consistency</li><li>Image forensics</li><li>Explainable analysis</li></ul></section></main><footer id="about"><div><strong>GLANCE</strong><p>A Single Glance Verifies the Truth</p></div><span>© 2026 Glance</span><nav><a href="#privacy">Privacy</a><a href="#security">Security</a><a href="#docs">Documentation</a><a href="#contact">Contact</a></nav></footer></div>
}
export default App

