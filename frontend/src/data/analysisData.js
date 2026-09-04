export const demoProfiles = {
  flagged: {
    verdict: 'LIKELY AI-GENERATED', confidence: 89, riskLevel: 'HIGH', tone: 'danger',
    message: 'Multiple forensic signals indicate characteristics commonly associated with synthetic or manipulated imagery.',
    signals: [
      ['AI Generation Detection', 87, 'Strong synthetic indicators'], ['Facial Consistency', 63, 'Some inconsistencies detected'],
      ['Skin / Texture Analysis', 81, 'Unusual texture patterns'], ['Image Compression', 72, 'Non-standard compression pattern'], ['Metadata', 48, 'Limited metadata available'],
    ],
    biometrics: [['Face detected', 'PASS'], ['Facial landmarks', 'PASS'], ['Facial symmetry', 'WARN'], ['Eye-region consistency', 'FLAGGED'], ['Face boundary consistency', 'FLAGGED']],
    reasons: [['Unusual facial texture', 'Skin texture contains patterns inconsistent with typical camera capture.'], ['Eye-region inconsistency', 'The eye region contains subtle structural inconsistencies.'], ['Face/background boundary anomaly', 'The transition between the face and background shows unusual artifacts.'], ['Unusual compression pattern', 'Compression characteristics differ from expected image patterns.']],
  },
  uncertain: {
    verdict: 'UNCERTAIN', confidence: 74, riskLevel: 'MEDIUM', tone: 'warning',
    message: 'Several signals are inconclusive. Manual verification is recommended.',
    signals: [['AI Generation Detection', 66, 'Mixed signal pattern'], ['Facial Consistency', 72, 'Mostly consistent'], ['Skin / Texture Analysis', 61, 'Needs review'], ['Image Compression', 58, 'Limited evidence'], ['Metadata', 42, 'Limited metadata available']],
    biometrics: [['Face detected', 'PASS'], ['Facial landmarks', 'PASS'], ['Facial symmetry', 'WARN'], ['Eye-region consistency', 'WARN'], ['Face boundary consistency', 'PASS']],
    reasons: [['Inconclusive visual signals', 'The available visual evidence does not support a decisive automated assessment.'], ['Limited metadata', 'The source image contains limited metadata for corroboration.']],
  },
  genuine: {
    verdict: 'LIKELY GENUINE', confidence: 91, riskLevel: 'LOW', tone: 'success',
    message: 'The image shows strong consistency across facial, texture, and forensic signals.',
    signals: [['AI Generation Detection', 12, 'Low synthetic indicators'], ['Facial Consistency', 91, 'Strong consistency'], ['Skin / Texture Analysis', 88, 'Natural capture patterns'], ['Image Compression', 82, 'Expected compression pattern'], ['Metadata', 76, 'Useful metadata available']],
    biometrics: [['Face detected', 'PASS'], ['Facial landmarks', 'PASS'], ['Facial symmetry', 'PASS'], ['Eye-region consistency', 'PASS'], ['Face boundary consistency', 'PASS']],
    reasons: [['Consistent capture characteristics', 'No high-risk visual anomalies were identified in this demo assessment.']],
  },
}

export const analysisStages = ['Image validation', 'Face detection', 'Biometric analysis', 'AI-generation analysis', 'Image forensics', 'Generating report']

