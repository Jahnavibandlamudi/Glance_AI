import { useEffect, useRef } from 'react'

export default function MagneticFieldBackground() {
  const canvasRef = useRef(null)
  useEffect(() => {
    const canvas = canvasRef.current; const ctx = canvas.getContext('2d'); let frame; let pointer = { x: -9999, y: -9999 }
    const reduced = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const particles = Array.from({ length: 105 }, (_, i) => ({ line: i % 7, t: Math.random(), speed: 0.00008 + Math.random() * 0.00011, size: 1 + Math.random() * 1.4 }))
    const resize = () => { const r = canvas.getBoundingClientRect(); const dpr = Math.min(devicePixelRatio || 1, 2); canvas.width = r.width * dpr; canvas.height = r.height * dpr; ctx.setTransform(dpr, 0, 0, dpr, 0, 0) }
    const draw = () => {
      const { width, height } = canvas.getBoundingClientRect(); ctx.clearRect(0, 0, width, height)
      particles.forEach((p, i) => { if (!reduced) p.t = (p.t + p.speed) % 1; const x = p.t * width; const y = height * (0.22 + p.line * 0.095) + Math.sin(p.t * Math.PI * 2 + p.line * 1.7) * (45 + p.line * 6); const dx = x - pointer.x; const dy = y - pointer.y; const near = Math.max(0, 1 - Math.hypot(dx, dy) / 180); const px = x + dx * near * 0.045; const py = y + dy * near * 0.045; const fade = Math.sin(Math.PI * p.t); ctx.globalAlpha = fade * (0.22 + (i % 3) * 0.07); ctx.fillStyle = i % 3 === 0 ? '#C9795D' : i % 3 === 1 ? '#E8B49A' : '#B8A9C9'; ctx.beginPath(); ctx.arc(px, py, p.size, 0, Math.PI * 2); ctx.fill() })
      if (!reduced) frame = requestAnimationFrame(draw)
    }
    resize(); draw(); addEventListener('resize', resize); const onMove = (e) => pointer = { x: e.clientX, y: e.clientY }; addEventListener('pointermove', onMove)
    return () => { cancelAnimationFrame(frame); removeEventListener('resize', resize); removeEventListener('pointermove', onMove) }
  }, [])
  return <canvas ref={canvasRef} className="magnetic-field" aria-hidden="true" />
}

