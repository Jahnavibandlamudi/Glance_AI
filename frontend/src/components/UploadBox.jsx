import { useEffect, useRef, useState } from 'react'

const maxSize = 10 * 1024 * 1024
const acceptedImageTypes = 'image/jpeg,image/png,image/webp,.jpg,.jpeg,.png,.webp'
const liveFrameCount = 5
const liveFrameDelayMs = 240
const formatSize = (bytes) => bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`
const wait = (ms) => new Promise((resolve) => setTimeout(resolve, ms))
const setBackgroundLowPower = (enabled) => {
  window.dispatchEvent(new CustomEvent('glance-background-low-power', { detail: enabled }))
}

export default function UploadBox({ file, onFile, onAnalyze }) {
  const input = useRef(null)
  const video = useRef(null)
  const canvas = useRef(null)
  const stream = useRef(null)
  const [error, setError] = useState('')
  const [dragging, setDragging] = useState(false)
  const [menu, setMenu] = useState(false)
  const [cameraOn, setCameraOn] = useState(false)
  const [capturing, setCapturing] = useState(false)

  const stopCamera = () => {
    stream.current?.getTracks().forEach((track) => track.stop())
    stream.current = null
    setCameraOn(false)
    setCapturing(false)
    setBackgroundLowPower(false)
  }

  useEffect(() => () => stopCamera(), [])
  useEffect(() => { if (cameraOn && video.current && stream.current) video.current.srcObject = stream.current }, [cameraOn])

  const select = (candidate) => {
    setBackgroundLowPower(false)
    setError('')
    if (!candidate) return
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(candidate.type)) return setError('Choose a JPG, PNG, or WebP image.')
    if (candidate.size > maxSize) return setError('Choose an image smaller than 10 MB.')
    const url = URL.createObjectURL(candidate)
    const image = new Image()
    image.onload = () => {
      if (file?.url) URL.revokeObjectURL(file.url)
      onFile({ raw: candidate, url, width: image.width, height: image.height, source: 'upload', liveFrames: [] })
    }
    image.onerror = () => {
      URL.revokeObjectURL(url)
      setError('This image could not be decoded.')
    }
    image.src = url
  }

  const startCamera = async () => {
    setError('')
    setMenu(false)
    setBackgroundLowPower(true)
    try {
      const media = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: 'user', width: { ideal: 640 }, height: { ideal: 480 }, frameRate: { ideal: 24, max: 30 } },
        audio: false,
      })
      stream.current = media
      setCameraOn(true)
    } catch {
      setError('Camera access was blocked or unavailable. Allow camera permission and try again.')
      setBackgroundLowPower(false)
    }
  }

  const openFilePicker = () => {
    setMenu(false)
    input.current.click()
  }

  const grabFrame = async (index) => {
    const width = video.current.videoWidth
    const height = video.current.videoHeight
    canvas.current.width = width
    canvas.current.height = height
    canvas.current.getContext('2d').drawImage(video.current, 0, 0, width, height)
    const blob = await new Promise((resolve) => canvas.current.toBlob(resolve, 'image/jpeg', 0.92))
    if (!blob) throw new Error('Could not capture a camera frame.')
    return new File([blob], `live-frame-${Date.now()}-${index}.jpg`, { type: 'image/jpeg' })
  }

  const capture = async (analyzeNow = false) => {
    if (!video.current || !canvas.current || capturing) return
    const width = video.current.videoWidth
    const height = video.current.videoHeight
    if (!width || !height) return setError('Wait for the camera preview before capturing.')
    setError('')
    setCapturing(true)
    try {
      const liveFrames = []
      for (let index = 0; index < liveFrameCount; index += 1) {
        liveFrames.push(await grabFrame(index))
        if (index < liveFrameCount - 1) await wait(liveFrameDelayMs)
      }
      const raw = liveFrames[Math.floor(liveFrames.length / 2)]
      const captured = {
        raw,
        url: URL.createObjectURL(raw),
        width,
        height,
        source: 'camera',
        liveFrames,
      }
      onFile(captured)
      stopCamera()
      if (analyzeNow) onAnalyze(captured)
    } catch (captureError) {
      setError(captureError.message || 'Could not capture a live sequence.')
      setCapturing(false)
    }
  }

  const drop = (event) => {
    event.preventDefault()
    setDragging(false)
    select(event.dataTransfer.files[0])
  }

  return <div className={`upload-box ${dragging ? 'is-dragging' : ''}`} onDragOver={(event) => { event.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={drop}>
    <input ref={input} type="file" accept={acceptedImageTypes} hidden onChange={(event) => select(event.target.files[0])} />
    {!file && !cameraOn ? <div className="upload-empty"><div className="upload-menu-wrap"><button className="plus-button" type="button" aria-label="Add an image" onClick={() => setMenu(!menu)}>+</button>{menu && <div className="upload-menu"><button type="button" onClick={openFilePicker}>Upload image</button><button type="button" onClick={startCamera}>Live capture</button></div>}</div><h3>Start an identity image check</h3><p>Drop an image, choose one from your device, or capture a live frame.</p><div className="upload-actions"><button type="button" className="text-button" onClick={openFilePicker}>Choose image</button><button type="button" className="text-button" onClick={startCamera}>Open camera</button></div></div> : null}
    {cameraOn ? <div className="camera-capture"><video ref={video} autoPlay playsInline muted /><canvas ref={canvas} hidden /><p className="camera-instruction">{capturing ? 'Scanning live presence...' : 'Face the camera naturally and hold steady while Glance captures a short sequence.'}</p><div className="camera-actions"><button type="button" className="remove-button" onClick={stopCamera} disabled={capturing}>Cancel</button><button type="button" className="text-button" onClick={() => capture(false)} disabled={capturing}>{capturing ? 'Capturing...' : 'Capture sequence'}</button><button type="button" className="analyze-button" onClick={() => capture(true)} disabled={capturing}>{capturing ? 'Scanning...' : 'Capture & analyze'} <span>→</span></button></div></div> : null}
    {file && !cameraOn ? <div className="upload-selected"><img src={file.url} alt="Selected identity image preview" /><div className="file-details"><div><strong>{file.raw.name}</strong><span>{file.raw.type.replace('image/', '').toUpperCase()} · {formatSize(file.raw.size)} · {file.width} × {file.height}{file.source === 'camera' ? ` · ${file.liveFrames?.length || 1} live frames` : ''}</span></div><button className="remove-button" type="button" onClick={() => onFile(null)}>Remove</button></div></div> : null}
    {error && <p className="upload-error" role="alert">{error}</p>}
    <div className="upload-footer"><span>Backend analysis</span><button type="button" className="analyze-button" disabled={!file} onClick={() => onAnalyze()}>Analyze image <span>→</span></button></div>
  </div>
}
