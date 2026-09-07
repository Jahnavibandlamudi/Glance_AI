import { useEffect, useRef } from 'react'
import * as THREE from 'three'

const prefersReducedMotion = () =>
  window.matchMedia?.('(prefers-reduced-motion: reduce)').matches

export default function MagneticFieldBackground() {
  const mountRef = useRef(null)

  useEffect(() => {
    const mount = mountRef.current
    if (!mount) return undefined

    const reduced = prefersReducedMotion()
    const scene = new THREE.Scene()
    const camera = new THREE.PerspectiveCamera(45, 1, 0.1, 100)
    camera.position.z = 15

    const renderer = new THREE.WebGLRenderer({
      antialias: false,
      alpha: true,
      powerPreference: 'high-performance',
    })
    renderer.setClearColor(0x000000, 0)
    renderer.setPixelRatio(Math.min(window.devicePixelRatio || 1, 1.25))
    mount.appendChild(renderer.domElement)

    const group = new THREE.Group()
    scene.add(group)

    const blue = new THREE.Color('#5e9dd3')
    const copper = new THREE.Color('#c9795d')
    const pearl = new THREE.Color('#e8b49a')
    const lineMaterials = []
    const fieldLines = []
    const lineCount = 16

    for (let line = 0; line < lineCount; line += 1) {
      const points = []
      const offset = (line - (lineCount - 1) / 2) * 0.72
      const phase = line * 0.58
      const sideWeight = Math.abs(line - (lineCount - 1) / 2) / (lineCount / 2)

      for (let i = 0; i < 72; i += 1) {
        const t = i / 71
        const y = (t - 0.5) * 15
        const wave = Math.sin(t * Math.PI * 5.2 + phase) * (0.34 + sideWeight * 0.46)
        const x = offset + wave
        const z = Math.cos(t * Math.PI * 2 + phase) * 0.9
        points.push(new THREE.Vector3(x, y, z))
      }

      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({
        color: line % 5 === 0 ? copper : blue,
        transparent: true,
        opacity: 0.22 + sideWeight * 0.2,
      })
      const mesh = new THREE.Line(geometry, material)
      mesh.userData = { phase, sideWeight }
      mesh.position.x = offset < 0 ? -3.2 : 3.2
      lineMaterials.push(material)
      fieldLines.push(mesh)
      group.add(mesh)
    }

    const particleCount = 140
    const particleGeometry = new THREE.BufferGeometry()
    const positions = new Float32Array(particleCount * 3)
    const particleData = []

    for (let i = 0; i < particleCount; i += 1) {
      const side = Math.random() > 0.5 ? 1 : -1
      const baseX = side * (3.6 + Math.random() * 5.3)
      const y = -7 + Math.random() * 14
      const z = -1.3 + Math.random() * 2.6
      positions.set([baseX, y, z], i * 3)
      particleData.push({
        baseX,
        y,
        z,
        speed: 0.16 + Math.random() * 0.38,
        phase: Math.random() * Math.PI * 2,
        drift: 0.36 + Math.random() * 0.7,
      })
    }

    particleGeometry.setAttribute('position', new THREE.BufferAttribute(positions, 3))
    const particleMaterial = new THREE.PointsMaterial({
      color: pearl,
      transparent: true,
      opacity: 0.7,
      size: 0.038,
      sizeAttenuation: true,
    })
    const particles = new THREE.Points(particleGeometry, particleMaterial)
    group.add(particles)

    const pulseRings = []
    const ringMaterial = new THREE.LineBasicMaterial({
      color: copper,
      transparent: true,
      opacity: 0.34,
    })

    for (let i = 0; i < 5; i += 1) {
      const geometry = new THREE.BufferGeometry()
      const points = []
      const radius = 0.18 + Math.random() * 0.22

      for (let step = 0; step <= 28; step += 1) {
        const angle = (step / 28) * Math.PI * 2
        points.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0))
      }

      geometry.setFromPoints(points)
      const ring = new THREE.Line(geometry, ringMaterial.clone())
      ring.position.set(
        (Math.random() > 0.5 ? 1 : -1) * (3.2 + Math.random() * 5.7),
        -6.4 + Math.random() * 12.8,
        -0.7 + Math.random() * 1.4,
      )
      ring.userData = {
        phase: Math.random() * Math.PI * 2,
        speed: 0.34 + Math.random() * 0.28,
        baseScale: 0.55 + Math.random() * 0.75,
      }
      pulseRings.push(ring)
      group.add(ring)
    }

    const traceObjects = []
    const makeTrace = (points, color, opacity = 0.28) => {
      const geometry = new THREE.BufferGeometry().setFromPoints(points)
      const material = new THREE.LineBasicMaterial({
        color,
        transparent: true,
        opacity,
      })
      const trace = new THREE.Line(geometry, material)
      traceObjects.push(trace)
      group.add(trace)
      return trace
    }

    for (let i = 0; i < 7; i += 1) {
      const size = 0.26 + Math.random() * 0.42
      const side = Math.random() > 0.5 ? 1 : -1
      const diamond = makeTrace(
        [
          new THREE.Vector3(0, size, 0),
          new THREE.Vector3(size, 0, 0),
          new THREE.Vector3(0, -size, 0),
          new THREE.Vector3(-size, 0, 0),
          new THREE.Vector3(0, size, 0),
        ],
        i % 3 === 0 ? copper : blue,
        0.18 + Math.random() * 0.16,
      )
      diamond.position.set(
        side * (2.4 + Math.random() * 6.4),
        -6.2 + Math.random() * 12.4,
        -0.9 + Math.random() * 1.8,
      )
      diamond.userData = {
        kind: 'diamond',
        phase: Math.random() * Math.PI * 2,
        speed: 0.14 + Math.random() * 0.2,
        float: 0.18 + Math.random() * 0.28,
      }
    }

    for (let i = 0; i < 6; i += 1) {
      const size = 0.38 + Math.random() * 0.36
      const gap = size * 0.48
      const points = [
        new THREE.Vector3(-size, -gap, 0),
        new THREE.Vector3(-size, -size, 0),
        new THREE.Vector3(-gap, -size, 0),
        new THREE.Vector3(gap, -size, 0),
        new THREE.Vector3(size, -size, 0),
        new THREE.Vector3(size, -gap, 0),
        new THREE.Vector3(size, gap, 0),
        new THREE.Vector3(size, size, 0),
        new THREE.Vector3(gap, size, 0),
        new THREE.Vector3(-gap, size, 0),
        new THREE.Vector3(-size, size, 0),
        new THREE.Vector3(-size, gap, 0),
      ]
      const reticle = makeTrace(points, i % 2 === 0 ? blue : copper, 0.16 + Math.random() * 0.14)
      reticle.position.set(
        (Math.random() > 0.5 ? 1 : -1) * (3.6 + Math.random() * 5.2),
        -6.6 + Math.random() * 13.2,
        -0.6 + Math.random() * 1.2,
      )
      reticle.userData = {
        kind: 'reticle',
        phase: Math.random() * Math.PI * 2,
        speed: 0.08 + Math.random() * 0.12,
        float: 0.14 + Math.random() * 0.2,
      }
    }

    for (let i = 0; i < 5; i += 1) {
      const points = []
      const nodeCount = 4 + Math.floor(Math.random() * 3)
      for (let node = 0; node < nodeCount; node += 1) {
        points.push(
          new THREE.Vector3(
            (Math.random() - 0.5) * 1.2,
            (Math.random() - 0.5) * 1.2,
            (Math.random() - 0.5) * 0.35,
          ),
        )
      }
      const fragment = makeTrace(points, i % 2 === 0 ? pearl : blue, 0.2)
      fragment.position.set(
        (Math.random() > 0.5 ? 1 : -1) * (4.2 + Math.random() * 4.8),
        -6.4 + Math.random() * 12.8,
        -0.8 + Math.random() * 1.6,
      )
      fragment.userData = {
        kind: 'fragment',
        phase: Math.random() * Math.PI * 2,
        speed: 0.2 + Math.random() * 0.18,
        float: 0.2 + Math.random() * 0.32,
      }
    }

    for (let i = 0; i < 5; i += 1) {
      const radius = 0.34 + Math.random() * 0.3
      const points = []

      for (let step = 0; step <= 6; step += 1) {
        const angle = (step / 6) * Math.PI * 2 + Math.PI / 6
        points.push(new THREE.Vector3(Math.cos(angle) * radius, Math.sin(angle) * radius, 0))
      }

      const hex = makeTrace(points, i % 2 === 0 ? blue : copper, 0.13 + Math.random() * 0.12)
      hex.position.set(
        (Math.random() > 0.5 ? 1 : -1) * (3.1 + Math.random() * 5.8),
        -6.5 + Math.random() * 13,
        -0.9 + Math.random() * 1.8,
      )
      hex.userData = {
        kind: 'hex',
        phase: Math.random() * Math.PI * 2,
        speed: 0.09 + Math.random() * 0.1,
        float: 0.1 + Math.random() * 0.18,
      }
    }

    for (let i = 0; i < 5; i += 1) {
      const points = []
      const radius = 0.34 + Math.random() * 0.38
      const start = Math.random() * Math.PI * 2
      const length = Math.PI * (0.45 + Math.random() * 0.55)

      for (let step = 0; step <= 16; step += 1) {
        const angle = start + (step / 16) * length
        const ripple = 1 + Math.sin(step * 0.75) * 0.035
        points.push(new THREE.Vector3(Math.cos(angle) * radius * ripple, Math.sin(angle) * radius * ripple, 0))
      }

      const arc = makeTrace(points, i % 3 === 0 ? pearl : blue, 0.18 + Math.random() * 0.16)
      arc.position.set(
        (Math.random() > 0.5 ? 1 : -1) * (2.8 + Math.random() * 5.9),
        -6.2 + Math.random() * 12.4,
        -0.6 + Math.random() * 1.2,
      )
      arc.userData = {
        kind: 'arc',
        phase: Math.random() * Math.PI * 2,
        speed: 0.18 + Math.random() * 0.18,
        float: 0.18 + Math.random() * 0.26,
      }
    }

    for (let i = 0; i < 7; i += 1) {
      const size = 0.2 + Math.random() * 0.22
      const plus = makeTrace(
        [
          new THREE.Vector3(-size, 0, 0),
          new THREE.Vector3(size, 0, 0),
          new THREE.Vector3(0, 0, 0),
          new THREE.Vector3(0, -size, 0),
          new THREE.Vector3(0, size, 0),
        ],
        i % 4 === 0 ? copper : blue,
        0.16 + Math.random() * 0.14,
      )
      plus.position.set(
        (Math.random() > 0.5 ? 1 : -1) * (2.5 + Math.random() * 6.5),
        -6.7 + Math.random() * 13.4,
        -0.7 + Math.random() * 1.4,
      )
      plus.userData = {
        kind: 'plus',
        phase: Math.random() * Math.PI * 2,
        speed: 0.24 + Math.random() * 0.22,
        float: 0.2 + Math.random() * 0.28,
      }
    }

    for (let i = 0; i < 8; i += 1) {
      const length = 0.22 + Math.random() * 0.42
      const dash = makeTrace(
        [
          new THREE.Vector3(-length, 0, 0),
          new THREE.Vector3(length, 0, 0),
        ],
        i % 3 === 0 ? pearl : blue,
        0.12 + Math.random() * 0.12,
      )
      dash.position.set(
        (Math.random() > 0.5 ? 1 : -1) * (3 + Math.random() * 6),
        -6.8 + Math.random() * 13.6,
        -0.8 + Math.random() * 1.6,
      )
      dash.userData = {
        kind: 'dash',
        phase: Math.random() * Math.PI * 2,
        speed: 0.26 + Math.random() * 0.26,
        float: 0.14 + Math.random() * 0.16,
      }
    }

    const pointer = { x: 0, y: 0, targetX: 0, targetY: 0 }
    let scrollProgress = 0
    let animationId = 0
    let visible = true
    let lowPower = false
    let lastRender = 0
    const frameInterval = 1000 / 30
    const lowPowerFrameInterval = 1000 / 6

    const updateSize = () => {
      const { width, height } = mount.getBoundingClientRect()
      renderer.setSize(width, height, false)
      camera.aspect = width / Math.max(height, 1)
      camera.updateProjectionMatrix()
    }

    const updateScroll = () => {
      const maxScroll = Math.max(document.documentElement.scrollHeight - window.innerHeight, 1)
      scrollProgress = window.scrollY / maxScroll
    }

    const onPointerMove = (event) => {
      pointer.targetX = (event.clientX / window.innerWidth - 0.5) * 2
      pointer.targetY = (event.clientY / window.innerHeight - 0.5) * 2
    }

    const onVisibilityChange = () => {
      visible = !document.hidden
      if (visible && !reduced) animate()
    }

    const setLowPower = (event) => {
      lowPower = Boolean(event.detail)
      renderer.setPixelRatio(lowPower ? 0.75 : Math.min(window.devicePixelRatio || 1, 1.25))
      if (lowPower) renderer.render(scene, camera)
      if (!lowPower && visible && !reduced) animate()
    }

    const revealObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach((entry) => {
          if (entry.isIntersecting) entry.target.classList.add('is-visible')
        })
      },
      { threshold: 0.14 },
    )

    document
      .querySelectorAll('.hero-section, .face-verify-section, .how-section, .trust-section, footer, .upload-box, .steps article')
      .forEach((element) => {
        element.classList.add('scroll-reveal')
        revealObserver.observe(element)
      })

    const clock = new THREE.Clock()
    const animate = () => {
      if (!visible) return
      const now = performance.now()
      const targetInterval = lowPower ? lowPowerFrameInterval : frameInterval
      if (now - lastRender < targetInterval) {
        animationId = requestAnimationFrame(animate)
        return
      }
      lastRender = now

      const elapsed = reduced ? 8 : clock.getElapsedTime()
      pointer.x += (pointer.targetX - pointer.x) * 0.035
      pointer.y += (pointer.targetY - pointer.y) * 0.035

      group.rotation.x = pointer.y * 0.08 + scrollProgress * 0.16
      group.rotation.y = pointer.x * 0.12 + Math.sin(elapsed * 0.2) * 0.035
      group.position.y = Math.sin(elapsed * 0.18) * 0.34 + scrollProgress * -2.3
      group.position.x = Math.sin(elapsed * 0.14) * 0.24
      group.scale.setScalar(1.18 + Math.sin(elapsed * 0.22) * 0.035 + scrollProgress * 0.18)

      fieldLines.forEach((line, index) => {
        const { phase, sideWeight } = line.userData
        line.position.y = Math.sin(elapsed * 0.52 + phase) * 0.42 + scrollProgress * 1.4
        line.position.x += Math.sin(elapsed * 0.35 + phase) * 0.002
        line.rotation.z = Math.sin(elapsed * 0.38 + phase) * 0.09
        line.material.opacity = 0.23 + sideWeight * 0.21 + Math.sin(elapsed * 1.1 + index) * 0.05
      })

      const particlePositions = particles.geometry.attributes.position.array
      particleData.forEach((particle, index) => {
        const nextY = ((particle.y + elapsed * particle.speed + scrollProgress * 5 + 7) % 14) - 7
        const wave = Math.sin(elapsed * 0.9 + particle.phase + nextY * 0.55) * particle.drift
        particlePositions[index * 3] = particle.baseX + wave
        particlePositions[index * 3 + 1] = nextY
        particlePositions[index * 3 + 2] = particle.z
      })
      particles.geometry.attributes.position.needsUpdate = true

      pulseRings.forEach((ring, index) => {
        const pulse = (Math.sin(elapsed * ring.userData.speed + ring.userData.phase) + 1) / 2
        ring.scale.setScalar(ring.userData.baseScale + pulse * 1.65)
        ring.position.y += Math.sin(elapsed * 0.32 + index) * 0.003 + scrollProgress * 0.0015
        ring.rotation.z = elapsed * 0.16 * (index % 2 === 0 ? 1 : -1)
        ring.material.opacity = 0.06 + (1 - pulse) * 0.22
      })

      traceObjects.forEach((trace, index) => {
        const { kind, phase, speed, float } = trace.userData
        const pulse = (Math.sin(elapsed * speed + phase) + 1) / 2
        trace.position.y += Math.sin(elapsed * 0.28 + phase) * 0.0025
        trace.position.x += Math.cos(elapsed * 0.18 + phase) * 0.0015
        const turnSpeed = kind === 'reticle' || kind === 'hex' ? 0.0018 : kind === 'dash' ? 0.0048 : 0.0034
        trace.rotation.z += turnSpeed * (index % 2 === 0 ? 1 : -1)
        trace.rotation.x = Math.sin(elapsed * 0.2 + phase) * 0.18
        trace.scale.setScalar(0.9 + pulse * float + scrollProgress * 0.12)
        trace.material.opacity = kind === 'fragment' || kind === 'dash' ? 0.1 + pulse * 0.18 : 0.1 + pulse * 0.22
      })

      renderer.render(scene, camera)
      if (!reduced) animationId = requestAnimationFrame(animate)
    }

    updateSize()
    updateScroll()
    animate()

    window.addEventListener('resize', updateSize)
    window.addEventListener('scroll', updateScroll, { passive: true })
    window.addEventListener('pointermove', onPointerMove, { passive: true })
    window.addEventListener('glance-background-low-power', setLowPower)
    document.addEventListener('visibilitychange', onVisibilityChange)

    return () => {
      cancelAnimationFrame(animationId)
      window.removeEventListener('resize', updateSize)
      window.removeEventListener('scroll', updateScroll)
      window.removeEventListener('pointermove', onPointerMove)
      window.removeEventListener('glance-background-low-power', setLowPower)
      document.removeEventListener('visibilitychange', onVisibilityChange)
      revealObserver.disconnect()
      fieldLines.forEach((line) => line.geometry.dispose())
      lineMaterials.forEach((material) => material.dispose())
      particleGeometry.dispose()
      particleMaterial.dispose()
      pulseRings.forEach((ring) => {
        ring.geometry.dispose()
        ring.material.dispose()
      })
      ringMaterial.dispose()
      traceObjects.forEach((trace) => {
        trace.geometry.dispose()
        trace.material.dispose()
      })
      renderer.dispose()
      renderer.domElement.remove()
    }
  }, [])

  return <div ref={mountRef} className="magnetic-field" aria-hidden="true" />
}

