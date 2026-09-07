import { useState } from 'react'
import MagneticFieldBackground from './components/MagneticFieldBackground'
import UploadBox from './components/UploadBox'
import AnalysisProgress from './components/AnalysisProgress'
import ResultDashboard from './components/ResultDashboard'
import FaceVerification from './components/FaceVerification'
import './App.css'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8010'
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

function App() {
  const [file, setFile] = useState(null); const [view, setView] = useState('landing'); const [result, setResult] = useState(null); const [progressPhase, setProgressPhase] = useState('intro')
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
    setResult(null); setProgressPhase('intro'); setView('progress')
    const introTimer = window.setTimeout(() => setProgressPhase('scanning'), 650)
    const body = new FormData()
    body.append('file', candidate.raw)
    body.append('source', candidate.source || 'upload')
    for (const frame of candidate.liveFrames || []) body.append('live_frames', frame)
    try {
      const response = await fetch(`${API_BASE_URL}/api/analyze/image`, { method: 'POST', body, signal: AbortSignal.timeout(45000) })
      const data = await response.json()
      if (!response.ok) throw new Error(data?.detail || 'Image analysis failed.')
      try {
        setResult(formatBackendResult(data))
      } catch (formatError) {
        setResult(formatBackendResult({
          verdict: data?.verdict || 'UNCERTAIN',
          confidence: data?.confidence ?? null,
          risk_level: data?.risk_level || 'MEDIUM',
          message: data?.message || `Report returned, but the UI had trouble formatting one field: ${formatError.message}`,
          details: data?.details || {},
        }))
      }
    } catch (error) {
      setResult(formatErrorResult(error))
    } finally {
      window.clearTimeout(introTimer)
      setProgressPhase('outro')
      await wait(700)
      setView('results')
    }
  }
  const reset = () => { if (file?.url) URL.revokeObjectURL(file.url); setFile(null); setResult(null); setView('landing') }
  if (view === 'progress') return <AnalysisProgress phase={progressPhase} />
  if (view === 'results' && result) return <ResultDashboard result={result} file={file} onReset={reset} onFeedback={sendFeedback} />
  return <div className="app"><MagneticFieldBackground /><header className="site-header"><a className="wordmark" href="#top">GLANCE</a><nav aria-label="Primary navigation"><a href="#product">Image analysis</a><a href="#identity">Face match</a><a href="#how-it-works">How it works</a><a href="#security">Security</a></nav><a className="header-cta" href="#identity">Verify identity</a></header><main id="top"><section className="hero-section" id="product"><p className="eyebrow">EXPLAINABLE IDENTITY SECURITY</p><h1>A Single Glance<br />Reviews the Evidence</h1><p className="hero-subtitle">Explainable AI-Powered KYC Deepfake Detection</p><p className="hero-copy">Analyze identity images for signs of AI generation, synthetic rendering, and camera replay risk — with reviewable model evidence instead of fixed demo decisions.</p><UploadBox file={file} onFile={setFile} onAnalyze={startAnalysis} /></section><FaceVerification apiBaseUrl={API_BASE_URL} /><section className="how-section" id="how-it-works"><p className="eyebrow">HOW IT WORKS</p><div className="section-heading"><h2>Clear evidence, before a decision.</h2><p>Glance organizes complex image signals into a calm, reviewable assessment.</p></div><div className="steps">{[['01','Upload','Upload an identity image or ID reference.'],['02','Capture','Capture a live selfie for liveness and face-match evidence.'],['03','Compare','Glance runs media models and FaceNet face embeddings.'],['04','Review','Use the separate evidence categories before making a decision.']].map(([num, title, copy]) => <article key={num}><span>{num}</span><h3>{title}</h3><p>{copy}</p></article>)}</div></section><section className="trust-section" id="security"><div><p className="eyebrow">TRUST, MADE MEASURABLE</p><h2>Security teams need more than a score.</h2><p>Glance brings AI-generation detection, synthetic-image domain checks, face matching, image forensics, metadata signals, and human-readable explanations into one considered review.</p></div><ul><li>AI-generation detection</li><li>Face embedding match</li><li>Camera liveness signal</li><li>Explainable analysis</li></ul></section></main><footer id="about"><div><strong>GLANCE</strong><p>A Single Glance Reviews the Evidence</p></div><span>© 2026 Glance</span><nav><a href="#privacy">Privacy</a><a href="#security">Security</a><a href="#docs">Documentation</a><a href="#contact">Contact</a></nav></footer></div>
}

const verdictTone = (verdict) => {
  if (verdict === 'LIKELY_AI_GENERATED') return 'danger'
  if (verdict === 'UNCERTAIN') return 'warning'
  return 'success'
}

const displayVerdict = (verdict) => String(verdict || 'UNCERTAIN').replaceAll('_', ' ')

const percent = (value) => value == null ? null : Math.round(value * 10000) / 100

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
  const authenticity = data.image_authenticity || {}
  const livePresence = data.live_presence || {}
  const isCamera = metrics.source === 'camera'
  const primaryVerdict = authenticity.verdict || data.verdict
  const primaryConfidence = authenticity.confidence ?? data.confidence
  const primaryMessage = authenticity.message || data.message
  const aiProbability = percent(metrics.visual_ai_probability)
  const realProbability = percent(metrics.visual_real_probability)
  const syntheticProbability = percent(metrics.synthetic_domain_probability)
  const liveScore = livePresence.confidence ?? (liveness.live_probability == null ? null : percent(liveness.live_probability))
  const modelName = metrics.visual_detector_feature_model || 'Unavailable'
  const probabilityText = aiProbability == null ? 'Unavailable' : `${aiProbability}% AI / ${realProbability}% real`
  const syntheticText = syntheticProbability == null ? 'Unavailable' : `${syntheticProbability}% synthetic/rendered`
  const liveText = liveScore == null ? 'Not assessed' : `${liveScore}% live`
  const timeline = [
    ['Image received', metadata.format ? `${metadata.format} · ${metadata.width || '?'} x ${metadata.height || '?'}` : 'Could not read image metadata', metadata.format ? 'PASS' : 'WARN'],
    ['Image authenticity', authenticity.message || (aiProbability == null ? 'Detector unavailable' : probabilityText), authenticity.verdict || metrics.visual_detector_status || 'UNKNOWN'],
    ['Synthetic domain check', syntheticProbability == null ? 'Unavailable' : syntheticText, syntheticProbability != null && syntheticProbability >= (metrics.thresholds?.high_synthetic_min_probability || 0.98) ? 'FLAGGED' : 'PASS'],
    ['Evidence fusion', fusion.explanation || data.message, data.verdict],
  ]
  if (isCamera) timeline.splice(3, 0, ['Live presence', livePresence.message || liveText, livePresence.prediction || liveness.prediction || liveness.status])
  const heatmapZones = [
    { label: 'Face area', left: '36%', top: '18%', width: '28%', height: '35%', tone: liveness.live_confirmed ? 'pass' : 'warn' },
    { label: 'Texture field', left: '18%', top: '60%', width: '32%', height: '24%', tone: aiProbability != null && aiProbability >= 65 ? 'flagged' : 'warn' },
    { label: 'Motion check', left: '63%', top: '54%', width: '24%', height: '28%', tone: liveness.prediction === 'POSSIBLE_PRESENTATION_ATTACK' ? 'flagged' : 'warn' },
    { label: 'Metadata', left: '7%', top: '10%', width: '22%', height: '18%', tone: metadata.has_exif || metadata.has_png_text ? 'pass' : 'warn' },
  ]

  return {
    verdict: displayVerdict(primaryVerdict),
    confidence: primaryConfidence,
    riskLevel: data.risk_level,
    tone: verdictTone(primaryVerdict),
    isCamera,
    isDemo: false,
    message: primaryMessage,
    authenticityAssessment: `Image authenticity: ${displayVerdict(authenticity.verdict || data.verdict)}. ${authenticity.message || probabilityText}`,
    cameraAssessment: isCamera ? `Live presence: ${(livePresence.prediction || liveness.prediction || liveness.status || 'UNAVAILABLE').replaceAll('_', ' ')}. ${livePresence.message || liveness.message || ''}` : null,
    replayAssessment: isCamera ? { status: livePresence.prediction || liveness.prediction || 'NOT_ASSESSED', score: liveScore, signals: [livePresence.message || liveness.message || 'Live-camera presentation checks use anti-spoof confidence and frame motion.'] } : null,
    timeline,
    heatmapZones,
    reviewQueueItem: {
      id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
      verdict: displayVerdict(primaryVerdict),
      riskLevel: data.risk_level,
      confidence: primaryConfidence,
      source: metrics.source || 'upload',
      replay: isCamera ? (livePresence.prediction || liveness.prediction || 'NOT_ASSESSED') : 'NOT_APPLICABLE',
      createdAt: new Date().toLocaleString(),
    },
    signals: [
      ['AI probability', aiProbability, `${modelName}: ${probabilityText}`],
      ['Real probability', realProbability, 'Model estimate; not proof of authenticity.'],
      ['Synthetic domain', syntheticProbability, `SigLIP: ${syntheticText}`],
      ...(isCamera ? [['Live presence', liveScore, livePresence.message || liveness.message || 'Live-camera liveness was assessed separately.']] : []),
    ],
    biometrics: [
      ['Image decoding', metadata.format ? 'PASS' : 'UNAVAILABLE'],
      ['Face landmarks', 'NOT ASSESSED'],
      ['Identity verification', 'NOT ASSESSED'],
      ...(isCamera ? [['Camera liveness', (livePresence.prediction || liveness.prediction || liveness.status || 'NOT_ASSESSED').replaceAll('_', ' ')]] : []),
    ],
    reasons: [[probabilityText, fusion.explanation || data.message], ...uniqueReasons(warnings, normalSignals, ['Model scope', details.model_evaluation?.scope || 'Validation scope unavailable.'])],
    forensicReview: [
      ['Model probability', probabilityText],
      ['Synthetic domain', syntheticText],
      ['Detector', modelName],
      ['Dimensions', metadata.width && metadata.height ? `${metadata.width} x ${metadata.height}` : 'Unreadable'],
      ['Container', metadata.format || 'Unknown'],
      ['Live capture', metrics.live_capture_score ? 'Yes' : 'No'],
      ['Embedded metadata', metadata.has_exif || metadata.has_png_text ? 'Present' : 'Limited'],
      ['Compression density', `${metrics.bytes_per_pixel ?? 'Unknown'} bytes/pixel`],
      ['Byte entropy', `${metrics.entropy ?? 'Unknown'} bits/byte`],
      ...(isCamera ? [
        ['Liveness', liveness.live_probability == null ? (liveness.status || 'Not assessed') : `${percent(liveness.live_probability)}% live / ${percent(liveness.spoof_probability)}% spoof`],
        ['Live frames', liveness.frame_count == null ? 'Not assessed' : `${liveness.assessed_frame_count || 0}/${liveness.frame_count} assessed`],
        ['Frame motion', liveness.frame_motion == null ? 'Not measured' : `${liveness.frame_motion}`],
      ] : []),
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
  replayAssessment: null,
  timeline: [
    ['Image received', 'The frontend prepared the request.', 'PASS'],
    ['Backend analysis', error.message || 'The backend could not analyze this image.', 'ERROR'],
  ],
  heatmapZones: [],
  reviewQueueItem: {
    id: `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    verdict: 'ANALYSIS FAILED',
    riskLevel: 'ERROR',
    confidence: 0,
    source: 'unknown',
    replay: 'NOT_ASSESSED',
    createdAt: new Date().toLocaleString(),
  },
  signals: [['Backend connection', 0, `Check that FastAPI is running on ${API_BASE_URL}.`]],
  biometrics: [['Request completed', 'FLAGGED']],
  reasons: [['Unable to complete analysis', 'The UI could not get a valid response from the backend.']],
  forensicReview: [['Backend connection', 'Failed']],
})

export default App

