import { useCallback, useEffect, useState } from 'react'
import MagneticFieldBackground from './MagneticFieldBackground'

const queueKey = 'glance-review-queue'

const statusTone = (status) => {
  const value = String(status || '').toUpperCase()
  if (value.includes('PASS') || value.includes('READY') || value.includes('LIKELY_LIVE') || value.includes('LIKELY_GENUINE')) return 'pass'
  if (value.includes('AI') || value.includes('REPLAY') || value.includes('FAILED') || value.includes('ERROR') || value.includes('FLAGGED')) return 'flagged'
  return 'warn'
}

const readQueue = () => {
  try { return JSON.parse(localStorage.getItem(queueKey) || '[]') }
  catch { return [] }
}

export default function ResultDashboard({ result, file, onReset, onFeedback }) {
  const [feedback, setFeedback] = useState('')
  const [queue, setQueue] = useState(() => readQueue())
  const [queued, setQueued] = useState(false)

  const addToQueue = useCallback((automatic = false) => {
    const item = {
      ...result.reviewQueueItem,
      filename: file?.raw?.name || 'camera-capture.jpg',
      preview: file?.url || '',
      reason: result.replayAssessment?.status?.includes('REPLAY') ? 'Possible photo replay' : result.verdict,
    }
    const next = [item, ...readQueue().filter((row) => row.id !== item.id)].slice(0, 12)
    localStorage.setItem(queueKey, JSON.stringify(next))
    setQueue(next)
    setQueued(true)
    if (!automatic) setFeedback('Added to human review queue.')
  }, [file?.raw?.name, file?.url, result.reviewQueueItem, result.replayAssessment?.status, result.verdict])

  useEffect(() => {
    if (result.riskLevel === 'LOW') return
    const timer = window.setTimeout(() => addToQueue(true), 0)
    return () => window.clearTimeout(timer)
  }, [addToQueue, result.riskLevel])

  const clearQueue = () => {
    localStorage.removeItem(queueKey)
    setQueue([])
    setQueued(false)
  }

  const correct = async (label) => {
    setFeedback('Saving correction...')
    try { await onFeedback(label); setFeedback('Saved for future training. Current prediction is unchanged.') }
    catch { setFeedback('Could not save correction.') }
  }
  return <main className="dashboard">
    <MagneticFieldBackground />
    <header className="dashboard-header"><button className="brand-button" onClick={onReset}>GLANCE</button><span>Image assessment</span><button className="new-check" onClick={onReset}>New check</button></header>
    <div className="dashboard-content">
      <section className={`result-summary ${result.tone}`}>
        <div><p className="eyebrow">IMAGE AUTHENTICITY</p><h1>{result.verdict}</h1><p>{result.message}</p>{result.cameraAssessment && <p><strong>{result.cameraAssessment}</strong></p>}</div>
        <div className="result-stats"><div><strong>{result.confidence == null ? 'N/A' : `${result.confidence}%`}</strong><span>model score</span></div><div><strong>{result.riskLevel}</strong><span>review priority</span></div></div>
      </section>
      <section className="correction-panel"><span>Correction feedback</span><div><button type="button" onClick={() => correct('real')}>Actually real</button><button type="button" onClick={() => correct('ai')}>Actually AI</button><button type="button" onClick={() => addToQueue(false)}>{queued ? 'Queued for review' : 'Send to review'}</button></div>{feedback && <p>{feedback}</p>}</section>
      <section className="grid two">
        <Panel title="Model Estimates"><div className="signal-list">{result.signals.map(([name, score, note]) => <div className="signal" key={name}><div><strong>{name}</strong><b>{score == null ? 'N/A' : `${score}%`}</b></div>{score != null && <div className="meter"><i style={{ width: `${score}%` }} /></div>}<p>{note}</p></div>)}</div></Panel>
        <Panel title="Verification Coverage"><div className="bio-list">{result.biometrics.map(([label, status]) => <div key={label}><span>{label}</span><b className={status === 'PASS' ? 'pass' : 'warn'}>{status}</b></div>)}</div></Panel>
      </section>
      <section className="grid two lower">
        <Panel title="Evidence Timeline"><div className="timeline">{result.timeline.map(([step, detail, status]) => <article key={step}><span className={statusTone(status)}>{status?.replaceAll?.('_', ' ') || 'UNKNOWN'}</span><div><strong>{step}</strong><p>{detail}</p></div></article>)}</div></Panel>
        {result.isCamera ? <Panel title="Live Presence"><div className="replay-card"><strong>{result.replayAssessment ? result.replayAssessment.status.replaceAll('_', ' ') : 'NOT ASSESSED'}</strong><b>{result.replayAssessment?.score == null ? 'N/A' : `${result.replayAssessment.score}%`}</b><p>{result.replayAssessment?.signals?.[0] || 'Live-camera presentation checks use anti-spoof confidence and frame motion.'}</p></div></Panel> : <Panel title="Upload Scope"><div className="replay-card"><strong>IMAGE ONLY</strong><b>N/A</b><p>Live presence is not assessed for uploaded files. This result is based on image-authenticity models and forensic metadata only.</p></div></Panel>}
      </section>
      <section className="grid two lower">
        <Panel title="Assessment Details">{result.reasons.map(([heading, copy]) => <article className="reason" key={heading}><div><strong>{heading}</strong>{copy && <p>{copy}</p>}</div></article>)}</Panel>
        <Panel title="Forensic Heatmap"><div className="anomaly-map forensic-map">{file?.url && <img src={file.url} alt="Submitted image with forensic regions" />}{result.heatmapZones.map((zone) => <i key={zone.label} className={`heat-zone ${zone.tone}`} style={{ left: zone.left, top: zone.top, width: zone.width, height: zone.height }}>{zone.label}</i>)}</div><div className="forensic-facts">{result.forensicReview.map(([label, value]) => <div key={label}><span>{label}</span><b>{value}</b></div>)}</div></Panel>
      </section>
      <section className="review-queue">
        <div><p className="eyebrow">HUMAN REVIEW QUEUE</p><h2>{queue.length} case{queue.length === 1 ? '' : 's'} waiting</h2></div>
        <button type="button" className="new-check" onClick={clearQueue} disabled={!queue.length}>Clear queue</button>
        <div className="queue-list">{queue.map((item) => <article key={item.id}><div>{item.preview && <img src={item.preview} alt="" />}<strong>{item.filename}</strong><span>{item.createdAt}</span></div><b className={statusTone(item.verdict)}>{item.riskLevel}</b><p>{item.reason} · {item.source} · {item.replay?.replaceAll?.('_', ' ')}</p></article>)}</div>
      </section>
    </div>
  </main>
}

function Panel({ title, children }) { return <section className="panel"><h2>{title}</h2>{children}</section> }
