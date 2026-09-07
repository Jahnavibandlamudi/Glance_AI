const phases = {
  intro: ['Initializing review', 'Preparing forensic evidence channels...'],
  scanning: ['Analyzing image', 'Running model, liveness, replay, metadata, and fusion checks...'],
  outro: ['Report ready', 'Assembling the final evidence view...'],
}

const steps = ['Decode', 'Model', 'Replay', 'Forensics', 'Fusion']

export default function AnalysisProgress({ phase = 'scanning' }) {
  const [title, copy] = phases[phase] || phases.scanning

  return <section className={`progress-screen ${phase}`} aria-live="polite" aria-busy={phase !== 'outro'}>
    <div className="progress-orbit" aria-hidden="true"><i /><i /><i /></div>
    <div className="progress-card">
      <p className="eyebrow">GLANCE</p>
      <h2>{title}</h2>
      <p className="progress-intro">{copy}</p>
      <div className="analysis-visual" aria-hidden="true">
        <span /><span /><span /><span />
        <b />
      </div>
      <div className="stages">
        {steps.map((step, index) => <div className={`stage ${phase === 'outro' || index < 2 ? 'done' : index === 2 ? 'current' : ''}`} key={step}><span>{index + 1}</span>{step}</div>)}
      </div>
    </div>
  </section>
}
