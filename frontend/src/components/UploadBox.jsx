import { useRef, useState } from 'react'

const maxSize = 10 * 1024 * 1024
const formatSize = (bytes) => bytes < 1024 * 1024 ? `${Math.ceil(bytes / 1024)} KB` : `${(bytes / 1024 / 1024).toFixed(1)} MB`

export default function UploadBox({ file, onFile, onAnalyze, demoProfile, setDemoProfile }) {
  const input = useRef(null); const [error, setError] = useState(''); const [dragging, setDragging] = useState(false); const [menu, setMenu] = useState(false)
  const select = (candidate) => { setError(''); if (!candidate?.type.startsWith('image/')) return setError('Choose a JPG, PNG, WebP, or other image file.'); if (candidate.size > maxSize) return setError('Choose an image smaller than 10 MB.'); const url = URL.createObjectURL(candidate); const image = new Image(); image.onload = () => onFile({ raw: candidate, url, width: image.width, height: image.height }); image.src = url }
  const drop = (e) => { e.preventDefault(); setDragging(false); select(e.dataTransfer.files[0]) }
  return <div className={`upload-box ${dragging ? 'is-dragging' : ''}`} onDragOver={(e) => { e.preventDefault(); setDragging(true) }} onDragLeave={() => setDragging(false)} onDrop={drop}>
    <input ref={input} type="file" accept="image/*" hidden onChange={(e) => select(e.target.files[0])} />
    {!file ? <div className="upload-empty"><div className="upload-menu-wrap"><button className="plus-button" type="button" aria-label="Add an image" onClick={() => setMenu(!menu)}>+</button>{menu && <div className="upload-menu"><button type="button" onClick={() => input.current.click()}>Upload image</button><span>Upload video <em>Coming next</em></span></div>}</div><h3>Start an identity image check</h3><p>Drop an image here, or choose one from your device.</p><button type="button" className="text-button" onClick={() => input.current.click()}>Choose image</button></div> : <div className="upload-selected"><img src={file.url} alt="Selected identity image preview" /><div className="file-details"><div><strong>{file.raw.name}</strong><span>{file.raw.type.replace('image/', '').toUpperCase()} · {formatSize(file.raw.size)} · {file.width} × {file.height}</span></div><button className="remove-button" type="button" onClick={() => onFile(null)}>Remove</button></div></div>}
    {error && <p className="upload-error" role="alert">{error}</p>}
    <div className="upload-footer"><span>Demo mode <select value={demoProfile} aria-label="Select demo result" onChange={(e) => setDemoProfile(e.target.value)}><option value="flagged">Flagged result</option><option value="uncertain">Uncertain result</option><option value="genuine">Genuine result</option></select></span><button type="button" className="analyze-button" disabled={!file} onClick={onAnalyze}>Analyze image <span>→</span></button></div>
  </div>
}

