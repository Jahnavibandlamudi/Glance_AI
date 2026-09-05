import { useEffect, useRef, useState } from 'react'

const maxSize = 10 * 1024 * 1024
const formatSize = (bytes) => bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`

export default function UploadBox({ file, onFile, onAnalyze }) {
  const input = useRef(null); const video = useRef(null); const canvas = useRef(null); const stream = useRef(null); const [error, setError] = useState(''); const [dragging, setDragging] = useState(false); const [menu, setMenu] = useState(false); const [cameraOn, setCameraOn] = useState(false)
  const stopCamera = () => { stream.current?.getTracks().forEach((track) => track.stop()); stream.current = null; setCameraOn(false) }
  useEffect(() => () => stopCamera(), [])
  useEffect(() => { if (cameraOn && video.current && stream.current) video.current.srcObject = stream.current }, [cameraOn])
  const select = (candidate) => { setError(''); if (!candidate) return; if (!['image/jpeg', 'image/png', 'image/webp'].includes(candidate.type)) return setError('Choose a JPG, PNG, or WebP image.'); if (candidate.size > maxSize) return setError('Choose an image smaller than 10 MB.'); const url = URL.createObjectURL(candidate); const image = new Image(); image.onload = () => { if (file?.url) URL.revokeObjectURL(file.url); onFile({ raw: candidate, url, width: image.width, height: image.height, source: 'upload' }) }; image.onerror = () => { URL.revokeObjectURL(url); setError('This image could not be decoded.') }; image.src = url }
  const startCamera = async () => { setError(''); setMenu(false); try { const media = await navigator.mediaDevices.getUserMedia({ video: { facingMode: 'user', width: { ideal: 1280 }, height: { ideal: 720 } }, audio: false }); stream.current = media; setCameraOn(true) } catch { setError('Camera access was blocked or unavailable. Allow camera permission and try again.') } }
  const capture = async (analyzeNow = false) => {
    if (!video.current || !canvas.current) return
    const width = video.current.videoWidth
    const height = video.current.videoHeight
    if (!width || !height) return setError('Wait for the camera preview before capturing.')
    canvas.current.width = width
    canvas.current.height = height
    canvas.current.getContext('2d').drawImage(video.current, 0, 0, width, height)
    const blob = await new Promise((resolve) => canvas.current.toBlob(resolve, 'image/jpeg', 0.92))
    if (!blob) return setError('Could not capture a camera frame.')
    const raw = new File([blob], `live-capture-${Date.now()}.jpg`, { type: 'image/jpeg' })
    const captured = { raw, url: URL.createObjectURL(raw), width, height, source: 'camera' }
    onFile(captured)
    stopCamera()
    if (analyzeNow) onAnalyze(captured)
  }
  const drop = (e) => { e.preventDefault(); setDragging(false); select(e.dataTransfer.files[0]) }
  return <div className={`upload-box ${dragging ? 'is-dragging' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={drop}>
    <input ref={input} type="file" accept="image/*" hidden onChange={(e) => select(e.target.files[0])} />
    {!file && !cameraOn ? <div className="upload-empty"><div className="upload-menu-wrap"><button className="plus-button" type="button" aria-label="Add an image" onClick={() => setMenu(!menu)}>+</button>{menu && <div className="upload-menu"><button type="button" onClick={() => input.current.click()}>Upload image</button><button type="button" onClick={startCamera}>Live capture</button></div>}</div><h3>Start an identity image check</h3><p>Drop an image, choose one from your device, or capture a live frame.</p><div className="upload-actions"><button type="button" className="text-button" onClick={() => input.current.click()}>Choose image</button><button type="button" className="text-button" onClick={startCamera}>Open camera</button></div></div> : null}
    {cameraOn ? <div className="camera-capture"><video ref={video} autoPlay playsInline muted /><canvas ref={canvas} hidden /><div className="camera-actions"><button type="button" className="remove-button" onClick={stopCamera}>Cancel</button><button type="button" className="text-button" onClick={() => capture(false)}>Capture photo</button><button type="button" className="analyze-button" onClick={() => capture(true)}>Capture & analyze <span>→</span></button></div></div> : null}
    {file && !cameraOn ? <div className="upload-selected"><img src={file.url} alt="Selected identity image preview" /><div className="file-details"><div><strong>{file.raw.name}</strong><span>{file.raw.type.replace('image/', '').toUpperCase()} · {formatSize(file.raw.size)} · {file.width} × {file.height}</span></div><button className="remove-button" type="button" onClick={() => onFile(null)}>Remove</button></div></div> : null}
    {error && <p className="upload-error" role="alert">{error}</p>}
    <div className="upload-footer"><span>Backend analysis</span><button type="button" className="analyze-button" disabled={!file} onClick={() => onAnalyze()}>Analyze image <span>→</span></button></div>
  </div>
}

