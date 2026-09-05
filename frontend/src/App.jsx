import { useState } from 'react'
import MagneticFieldBackground from './components/MagneticFieldBackground'
import UploadBox from './components/UploadBox'
import AnalysisProgress from './components/AnalysisProgress'
import ResultDashboard from './components/ResultDashboard'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8010'

function App() {
  const [file, setFile] = useState(null); const [view, setView] = useState('landing'); const [result, setResult] = useState(null)
  const sendFeedback = async (label) => {
    if (!file?.raw) return
    const body = new FormData()
    body.append('label', label)
    body.append('file', file.raw)
    const response = await fetch(`${API_BASE_URL}/api/analyze/image/feedback`, { method: 'POST', body })
    if (!response.ok) throw new Error('Could not save feedback.')
  }
  const startAnalysis = async (candidate = file) => {
    if (!candidate?.raw) return
    setResult(null); setView('progress')
    const body = new FormData()
    body.append('file', candidate.raw)
    body.append('source', candidate.source || 'upload')
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze/image`, { method: 'POST', body, signal: AbortSignal.timeout(60000) })
      const data = await response.json()
      if (!response.ok) throw new Error(data?.detail || 'Image analysis failed.')
      setResult(formatBackendResult(data))
    } catch (error) {
      setResult(formatErrorResult(error))
    } finally {
      setView('results')
    }
  }
  const reset = () => { if (file?.url) URL.revokeObjectURL(file.url); setFile(null); setResult(null); setView('landing') }
  if (view === 'progress') return <AnalysisProgress />
  if (view === 'results' && result) return <ResultDashboard result={result} file={file} onReset={reset} onFeedback={sendFeedback} />
  return <div className="app"><MagneticFieldBackground /><header className="site-header"><a className="wordmark" href="#top">GLANCE</a><nav aria-label="Primary navigation"><a href="#product">Product</a><a href="#how-it-works">How it works</a><a href="#security">Security</a><a href="#about">About</a></nav><a className="header-cta" href="#product">Verify an image</a></header><main id="top"><section className="hero-section" id="product"><p className="eyebrow">EXPLAINABLE IDENTITY SECURITY</p><h1>A Single Glance<br />Verifies the Truth</h1><p className="hero-subtitle">Explainable AI-Powered KYC Deepfake Detection</p><p className="hero-copy">Analyze identity images for signs of AI generation, manipulation, and biometric inconsistencies — with explainable forensic signals instead of black-box decisions.</p><UploadBox file={file} onFile={setFile} onAnalyze={startAnalysis} /></section><section className="how-section" id="how-it-works"><p className="eyebrow">HOW IT WORKS</p><div className="section-heading"><h2>Clear evidence, before a decision.</h2><p>Glance organizes complex image signals into a calm, reviewable assessment.</p></div><div className="steps">{[['01','Upload','Upload or live capture an identity image.'],['02','Analyze','Glance examines biometric and forensic signals.'],['03','Explain','The system identifies suspicious patterns.'],['04','Verify','Review the risk assessment before making a decision.']].map(([num, title, copy]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{copy}</p></article>)}</div></section><section className="trust-section" id="security"><div><p className="eyebrow">TRUST, MADE MEASURABLE</p><h2>Security teams need more than a score.</h2><p>Glance brings AI-generation detection, biometric consistency, image forensics, metadata signals, and human-readable explanations into one considered review.</p></div><ul><li>AI-generation detection</li><li>Biometric consistency</li><li>Image forensics</li><li>Explainable analysis</li></ul></section></main><footer id="about"><div><strong>GLANCE</strong><p>A Single Glance Verifies the Truth</p></div><span>© 2026 Glance</span><nav><a href="#privacy">Privacy</a><a href="#security">Security</a><a href="#docs">Documentation</a><a href="#contact">Contact</a></nav></footer></div>
}

const verdictTone = (verdict) => {
  if (verdict === 'LIKELY_AI_GENERATED') return 'danger'
  if (verdict === 'UNCERTAIN') return 'warning'
  return 'success'
}

const displayVerdict = (verdict) => verdict.replaceAll('_', ' ')

const percent = (value) => value == null ? null : Math.round(value * 1000) / 10

const uniqueReasons = (warnings, normalSignals, fallback) => {
  const rows = [...new Set(warnings)].map((warning) => [warning, ''])
  return rows.length ? rows : [fallback]
}

const formatBackendResult = (data) => {
  const details = data.details || {}
  const ai = details.ai_generated_image_detection || {}
  const biometrics = details.facial_biometric_analysis || {}
  const forensics = details.forensic_analysis || {}
  const fusion = details.evidence_fusion || {}
  const warnings = [...(ai.warnings || []), ...(biometrics.warnings || []), ...(forensics.warnings || [])]
  const normalSignals = [...(ai.normal_signals || []), ...(biometrics.normal_signals || []), ...(forensics.normal_signals || [])]
  const metadata = forensics.metadata || {}
  const metrics = ai.metrics || {}
  const liveness = details.liveness || {}
  const aiProbability = percent(metrics.visual_ai_probability)
  const realProbability = percent(metrics.visual_real_probability)
  const modelName = metrics.visual_detector_feature_model || 'Unavailable'
  const probabilityText = aiProbability == null ? 'Unavailable' : `${aiProbability}% AI / ${realProbability}% real`

  return {
    verdict: displayVerdict(data.verdict),
    confidence: data.confidence,
    riskLevel: data.risk_level,
    tone: verdictTone(data.verdict),
    isDemo: false,
    message: fusion.explanation || data.message,
    cameraAssessment: metrics.source === 'camera' ? `Camera replay check: ${(liveness.prediction || liveness.status || 'UNAVAILABLE').replaceAll('_', ' ')}. ${liveness.message || ''}` : null,
    signals: [
      ['AI probability', aiProbability, `${modelName}: ${probabilityText}`],
      ['Real probability', realProbability, 'Model estimate; not proof of authenticity.'],
    ],
    biometrics: [
      ['Image decoding', metadata.format ? 'PASS' : 'UNAVAILABLE'],
      ['Face landmarks', 'NOT ASSESSED'],
      ['Identity verification', 'NOT ASSESSED'],
      ['Camera liveness / replay', (liveness.prediction || liveness.status || 'NOT_ASSESSED').replaceAll('_', ' ')],
    ],
    reasons: [[probabilityText, fusion.explanation || data.message], ...uniqueReasons(warnings, normalSignals, ['Model scope', details.model_evaluation?.scope || 'Validation scope unavailable.'])],
    forensicReview: [
      ['Model probability', probabilityText],
      ['Detector', modelName],
      ['Dimensions', metadata.width && metadata.height ? `${metadata.width} x ${metadata.height}` : 'Unreadable'],
      ['Container', metadata.format || 'Unknown'],
      ['Live capture', metrics.live_capture_score ? 'Yes' : 'No'],
      ['Embedded metadata', metadata.has_exif || metadata.has_png_text ? 'Present' : 'Limited'],
      ['Compression density', `${metrics.bytes_per_pixel ?? 'Unknown'} bytes/pixel`],
      ['Byte entropy', `${metrics.entropy ?? 'Unknown'} bits/byte`],
      ['Liveness', liveness.live_probability == null ? (liveness.status || 'Not assessed') : `${percent(liveness.live_probability)}% live / ${percent(liveness.spoof_probability)}% spoof`],
      ['Held-out face test', details.model_evaluation?.test ? `${percent(details.model_evaluation.test.accuracy)}% on ${details.model_evaluation.test_rows} images` : 'Unavailable'],
    ],
  }
}

const formatErrorResult = (error) => ({
  verdict: 'ANALYSIS FAILED',
  confidence: 0,
  riskLevel: 'ERROR',
  tone: 'danger',
  isDemo: false,
  message: error.message || 'The backend could not analyze this image.',
  signals: [['Backend connection', 0, `Check that FastAPI is running on ${API_BASE_URL}.`]],
  biometrics: [['Request completed', 'FLAGGED']],
  reasons: [['Unable to complete analysis', 'The UI could not get a valid response from the backend.']],
  forensicReview: [['Backend connection', 'Failed']],
})

export default App

