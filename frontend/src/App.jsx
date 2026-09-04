import { useEffect, useState } from 'react'
import MagneticFieldBackground from './components/MagneticFieldBackground'
import UploadBox from './components/UploadBox'
import AnalysisProgress from './components/AnalysisProgress'
import ResultDashboard from './components/ResultDashboard'
import { analysisStages } from './data/analysisData'
import './App.css'

function App() {
  const [file, setFile] = useState(null); const [view, setView] = useState('landing'); const [stage, setStage] = useState(0); const [result, setResult] = useState(null)
  useEffect(() => { if (view !== 'progress') return; const timer = setTimeout(() => setStage(s => Math.min(s + 1, analysisStages.length - 1)), 480); return () => clearTimeout(timer) }, [view, stage])
  const startAnalysis = async () => {
    if (!file?.raw) return
    setStage(0); setResult(null); setView('progress')
    const body = new FormData()
    body.append('file', file.raw)
    try {
      const response = await fetch('http://127.0.0.1:8000/api/analyze/image', { method: 'POST', body })
      const data = await response.json()
      if (!response.ok) throw new Error(data?.detail || 'Image analysis failed.')
      setResult(formatBackendResult(data))
    } catch (error) {
      setResult(formatErrorResult(error))
    } finally {
      setStage(analysisStages.length)
      setTimeout(() => setView('results'), 250)
    }
  }
  const reset = () => { if (file?.url) URL.revokeObjectURL(file.url); setFile(null); setResult(null); setView('landing'); setStage(0) }
  if (view === 'progress') return <AnalysisProgress stage={stage} />
  if (view === 'results' && result) return <ResultDashboard result={result} file={file} onReset={reset} />
  return <div className="app"><MagneticFieldBackground /><header className="site-header"><a className="wordmark" href="#top">GLANCE</a><nav aria-label="Primary navigation"><a href="#product">Product</a><a href="#how-it-works">How it works</a><a href="#security">Security</a><a href="#about">About</a></nav><a className="header-cta" href="#product">Verify an image</a></header><main id="top"><section className="hero-section" id="product"><p className="eyebrow">EXPLAINABLE IDENTITY SECURITY</p><h1>A Single Glance<br />Verifies the Truth</h1><p className="hero-subtitle">Explainable AI-Powered KYC Deepfake Detection</p><p className="hero-copy">Analyze identity images for signs of AI generation, manipulation, and biometric inconsistencies — with explainable forensic signals instead of black-box decisions.</p><UploadBox file={file} onFile={setFile} onAnalyze={startAnalysis} /></section><section className="how-section" id="how-it-works"><p className="eyebrow">HOW IT WORKS</p><div className="section-heading"><h2>Clear evidence, before a decision.</h2><p>Glance organizes complex image signals into a calm, reviewable assessment.</p></div><div className="steps">{[['01','Upload','Upload an identity image.'],['02','Analyze','Glance examines biometric and forensic signals.'],['03','Explain','The system identifies suspicious patterns.'],['04','Verify','Review the risk assessment before making a decision.']].map(([num, title, copy]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{copy}</p></article>)}</div></section><section className="trust-section" id="security"><div><p className="eyebrow">TRUST, MADE MEASURABLE</p><h2>Security teams need more than a score.</h2><p>Glance brings AI-generation detection, biometric consistency, image forensics, metadata signals, and human-readable explanations into one considered review.</p></div><ul><li>AI-generation detection</li><li>Biometric consistency</li><li>Image forensics</li><li>Explainable analysis</li></ul></section></main><footer id="about"><div><strong>GLANCE</strong><p>A Single Glance Verifies the Truth</p></div><span>© 2026 Glance</span><nav><a href="#privacy">Privacy</a><a href="#security">Security</a><a href="#docs">Documentation</a><a href="#contact">Contact</a></nav></footer></div>
}

const verdictTone = (verdict) => {
  if (verdict === 'LIKELY_AI_GENERATED') return 'danger'
  if (verdict === 'UNCERTAIN') return 'warning'
  return 'success'
}

const displayVerdict = (verdict) => verdict.replaceAll('_', ' ')

const firstNote = (values, fallback) => values?.[0] || fallback

const formatBackendResult = (data) => {
  const details = data.details || {}
  const ai = details.ai_generated_image_detection || {}
  const biometrics = details.facial_biometric_analysis || {}
  const forensics = details.forensic_analysis || {}
  const fusion = details.evidence_fusion || {}
  const warnings = [...(ai.warnings || []), ...(biometrics.warnings || []), ...(forensics.warnings || [])]
  const normalSignals = [...(ai.normal_signals || []), ...(biometrics.normal_signals || []), ...(forensics.normal_signals || [])]
  const metadata = forensics.metadata || {}

  return {
    verdict: displayVerdict(data.verdict),
    confidence: data.confidence,
    riskLevel: data.risk_level,
    tone: verdictTone(data.verdict),
    isDemo: false,
    message: fusion.explanation || data.message,
    signals: [
      ['AI Generation Detection', ai.score ?? 0, firstNote(ai.warnings, firstNote(ai.normal_signals, 'No strong synthetic indicators reported.'))],
      ['Image Container', metadata.format ? 100 : 0, metadata.format ? `Valid ${metadata.format} image` : 'Image format could not be confirmed.'],
      ['Compression / Entropy', Math.round(ai.metrics?.entropy ? Math.min(ai.metrics.entropy * 12.5, 100) : 0), firstNote(ai.warnings, 'Compression and byte patterns look acceptable.')],
      ['Metadata', metadata.has_exif || metadata.has_png_text ? 76 : 35, metadata.has_exif || metadata.has_png_text ? 'Metadata is present.' : 'Limited metadata available.'],
      ['Evidence Fusion', fusion.score ?? ai.score ?? 0, `${fusion.warning_count ?? warnings.length} suspicious signal${(fusion.warning_count ?? warnings.length) === 1 ? '' : 's'} found.`],
    ],
    biometrics: [
      ['Resolution check', biometrics.status === 'passed' ? 'PASS' : 'WARN'],
      ['Face landmark model', 'WARN'],
      ['Container support', forensics.status === 'implemented' ? 'PASS' : 'WARN'],
      ['File integrity', data.risk_level === 'HIGH' ? 'FLAGGED' : 'PASS'],
      ['Manual review', data.verdict === 'UNCERTAIN' ? 'WARN' : 'PASS'],
    ],
    reasons: warnings.length
      ? warnings.map((warning) => [warning, 'This signal contributed to the final conservative risk score.'])
      : [[firstNote(normalSignals, 'No high-risk indicators'), 'The backend did not find enough independent suspicious signals to flag this image as AI-generated.']],
  }
}

const formatErrorResult = (error) => ({
  verdict: 'ANALYSIS FAILED',
  confidence: 0,
  riskLevel: 'ERROR',
  tone: 'danger',
  isDemo: false,
  message: error.message || 'The backend could not analyze this image.',
  signals: [['Backend connection', 0, 'Check that FastAPI is running on http://127.0.0.1:8000.']],
  biometrics: [['Request completed', 'FLAGGED']],
  reasons: [['Unable to complete analysis', 'The UI could not get a valid response from the backend.']],
})

export default App

