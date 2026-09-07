import { useEffect, useRef, useState } from 'react'

const maxSize = 10 * 1024 * 1024
const acceptedImageTypes = 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp'
const liveFrameCount = 5
const liveFrameDelayMs = 240
const formatSize = (bytes) => bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

const verificationMessage = (error) => {
  if (error?.name === 'TimeoutError' || String(error?.message || '').toLowerCase().includes('timed out')) {
    return 'Face verification timed out while waiting for the backend. If this is the first run, install the FaceNet weights with: python -m backend.training.setup_face_match'
  }
  return error?.message || error?.detail?.message || 'Face verification failed.'
}

export default function FaceVerification({ apiBaseUrl }) {
  const referenceInput = useRef(null)
  const video = useRef(null)
  const canvas = useRef(null)
  const stream = useRef(null)
  const [reference, setReference] = useState(null)
  const [selfie, setSelfie] = useState(null)
  const [cameraOn, setCameraOn] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)

  const stopCamera = () => {
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
    setCameraOn(false)
  }

  useEffect(() => () => stopCamera(), [])
  useEffect(() => { if (cameraOn && video.current && stream.current) video.current.srcObject = stream.current }, [cameraOn])

  const selectReference = (candidate) => {
    setError('')
    setResult(null)
    if (!candidate) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(candidate.type)) return setError('Please upload a JPG, PNG, or WebP reference photo.')
    if (candidate.size > maxSize) return setError('Please upload a reference photo smaller than 10 MB.')
    const url = URL.createObjectURL(candidate)
    const image = new Image()
    image.onload = () => setReference({ raw: candidate, url, width: image.width, height: image.height })
    image.onerror = () => { URL.revokeObjectURL(url); setError('The reference photo could not be decoded.') }
    image.src = url
  }

  const startCamera = async () => {
    setError('')
    setResult(null)
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      stream.current = media
      setCameraOn(true)
    } catch {
      setError('Camera access was blocked or unavailable.')
    }
  }

  const grabFrame = async (index) => {
    if (!video.current || !canvas.current) return
    const width = video.current.videoWidth
    const height = video.current.videoHeight
    if (!width || !height) throw new Error('Wait for the camera preview before capturing.')
    canvas.current.width = width
    canvas.current.height = height
    canvas.current.getContext('2d').drawImage(video.current, 0, 0, width, height)
    const blob = await new Promise((resolve) => canvas.current.toBlob(resolve, 'image/jpeg', 0.92))
    if (!blob) throw new Error('Could not capture a live selfie.')
    return { file: new File([blob], `identity-selfie-frame-${Date.now()}-${index}.jpg`, { type: 'image/jpeg' }), width, height }
  }

  const captureSelfie = async () => {
    setError('')
    try {
      const frames = []
      for (let index = 0; index < liveFrameCount; index += 1) {
        frames.push(await grabFrame(index))
        if (index < liveFrameCount - 1) await wait(liveFrameDelayMs)
      }
      const selected = frames[Math.floor(frames.length / 2)]
      setSelfie({
        raw: selected.file,
        url: URL.createObjectURL(selected.file),
        width: selected.width,
        height: selected.height,
        liveFrames: frames.map((frame) => frame.file),
      })
      stopCamera()
    } catch (captureError) {
      setError(captureError.message || 'Could not capture a live selfie sequence.')
    }
  }

  const verify = async () => {
    if (!reference) return setError('Please upload a reference photo.')
    if (!selfie) return setError('Please capture a live selfie.')
    setBusy(true)
    setError('')
    setResult(null)
    try {
      const body = new FormData()
      body.append('reference_image', reference.raw)
      body.append('selfie_image', selfie.raw)
      for (const frame of selfie.liveFrames || []) body.append('selfie_live_frames', frame)
      const response = await fetch(`${apiBaseUrl}/api/verify/face-match`, { method: 'POST', body, signal: AbortSignal.timeout(90000) })
      const data = await response.json()
      if (!response.ok) throw data?.detail || data
      setResult(data)
    } catch (verificationError) {
      setError(verificationMessage(verificationError))
    } finally {
      setBusy(false)
    }
  }

  const decisionClass = result?.decision === 'MATCH' ? 'pass' : result?.decision === 'MISMATCH' ? 'flagged' : 'warn'

  return <section className="face-verify-section" id="identity">
    <p className="eyebrow">IDENTITY VERIFICATION</p>
    <div className="section-heading"><h2>Match the ID photo to a live selfie.</h2><p>Face match, media authenticity, and liveness stay separate so the review is honest.</p></div>
    <div className="face-verify-grid">
      <article className="verify-panel">
        <span>Reference / ID photo</span>
        {reference ? <Preview item={reference} /> : <button type="button" className="verify-drop" onClick={() => referenceInput.current.click()}>Upload reference image</button>}
        <input ref={referenceInput} type="file" accept={acceptedImageTypes} hidden onChange={(event) => selectReference(event.target.files[0])} />
      </article>
      <div className="verify-vs">VS</div>
      <article className="verify-panel">
        <span>Live selfie</span>
        {cameraOn ? <div className="verify-camera"><video ref={video} autoPlay playsInline muted /><canvas ref={canvas} hidden /><button type="button" className="analyze-button" onClick={captureSelfie}>Capture selfie <span>→</span></button></div> : selfie ? <Preview item={selfie} /> : <button type="button" className="verify-drop" onClick={startCamera}>Open camera</button>}
      </article>
    </div>
    <div className="verify-actions">
      <button type="button" className="analyze-button" disabled={busy || !reference || !selfie} onClick={verify}>{busy ? 'Verifying...' : 'Verify identity'} <span>→</span></button>
      {selfie && <button type="button" className="text-button" onClick={startCamera}>Retake selfie</button>}
    </div>
    {error && <p className="upload-error" role="alert">{error}</p>}
    {result && <section className={`match-result ${decisionClass}`}>
      <div><p className="eyebrow">FACE MATCH RESULT</p><h3>{result.decision}</h3><p>{result.message}</p></div>
      <strong>{result.match_score}%</strong>
      <div className="match-facts">
        <span>Cosine similarity <b>{result.similarity}</b></span>
        <span>Reference face <b>{result.reference_face_count}</b></span>
        <span>Selfie face <b>{result.selfie_face_count}</b></span>
        <span>Liveness <b>{(result.liveness?.prediction || result.liveness?.status || 'NOT_ASSESSED').replaceAll('_', ' ')}</b></span>
        <span>Risk <b>{result.risk_level}</b></span>
      </div>
    </section>}
  </section>
}

function Preview({ item }) {
  return <div className="verify-preview"><img src={item.url} alt="" /><span>{item.raw.name}</span><b>{formatSize(item.raw.size)} · {item.width} x {item.height}{item.liveFrames?.length ? ` · ${item.liveFrames.length} live frames` : ''}</b></div>
}
