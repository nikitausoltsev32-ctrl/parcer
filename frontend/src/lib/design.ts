// Design tokens matching the Lida aero/glass design system
export const G = {
  // Backgrounds
  glassCard:    'rgba(255,255,255,0.55)',
  glassCardHov: 'rgba(255,255,255,0.68)',
  glassSidebar: 'rgba(255,255,255,0.18)',
  glassInput:   'rgba(255,255,255,0.60)',
  glassHeader:  'rgba(255,255,255,0.45)',
  glassModal:   'rgba(245,248,252,0.88)',
  glassRow:     'rgba(255,255,255,0.35)',
  glassRowHov:  'rgba(255,255,255,0.55)',

  // Borders
  border:       '1px solid rgba(255,255,255,0.70)',
  borderSubtle: '1px solid rgba(255,255,255,0.40)',
  borderDark:   '1px solid rgba(30,50,90,0.10)',

  // Navy
  navy:         '#1a2540',
  navyMid:      '#2e3f6e',
  navyLight:    '#4a6fa5',
  navyXLight:   'rgba(26,37,64,0.08)',

  // Text
  textPrimary:   '#1a2030',
  textSecondary: '#4a5568',
  textMuted:     '#8a96a8',

  // Colors
  green:    '#2d7a5f',
  greenBg:  'rgba(45,122,95,0.10)',
  amber:    '#b07d2a',
  amberBg:  'rgba(176,125,42,0.10)',
  red:      '#c0392b',
  redBg:    'rgba(192,57,43,0.10)',
  purple:   '#6b46c1',
  purpleBg: 'rgba(107,70,193,0.10)',
  blue:     '#2b6cb0',
  blueBg:   'rgba(43,108,176,0.10)',

  // Effects
  blur:      'blur(18px) saturate(1.4)',
  blurHeavy: 'blur(28px) saturate(1.6)',
  radius:    '14px',
  radiusSm:  '10px',
  radiusXs:  '7px',

  // Shadows
  shadow:      '0 4px 24px rgba(20,40,80,0.10), 0 1px 4px rgba(20,40,80,0.06)',
  shadowCard:  '0 2px 16px rgba(20,40,80,0.08), 0 1px 3px rgba(20,40,80,0.04)',
  shadowModal: '0 24px 80px rgba(20,40,80,0.18), 0 4px 16px rgba(20,40,80,0.08)',
  shadowBtn:   '0 2px 8px rgba(26,37,64,0.18)',
};

export const SOURCE_BADGE: Record<string, { bg: string; text: string; border: string }> = {
  'serpapi':     { bg: 'rgba(45,122,95,0.12)',   text: '#2d7a5f', border: 'rgba(45,122,95,0.25)'  },
  'SerpAPI':     { bg: 'rgba(45,122,95,0.12)',   text: '#2d7a5f', border: 'rgba(45,122,95,0.25)'  },
  'serp_maps':   { bg: 'rgba(45,122,95,0.12)',   text: '#2d7a5f', border: 'rgba(45,122,95,0.25)'  },
  'serp_google': { bg: 'rgba(45,122,95,0.12)',   text: '#2d7a5f', border: 'rgba(45,122,95,0.25)'  },
  'serp_yandex': { bg: 'rgba(192,57,43,0.12)',   text: '#c0392b', border: 'rgba(192,57,43,0.25)'  },
  'firecrawl': { bg: 'rgba(176,125,42,0.12)',  text: '#b07d2a', border: 'rgba(176,125,42,0.25)' },
  'Firecrawl': { bg: 'rgba(176,125,42,0.12)',  text: '#b07d2a', border: 'rgba(176,125,42,0.25)' },
  'csv':       { bg: 'rgba(107,70,193,0.12)',  text: '#6b46c1', border: 'rgba(107,70,193,0.25)' },
  'CSV':       { bg: 'rgba(107,70,193,0.12)',  text: '#6b46c1', border: 'rgba(107,70,193,0.25)' },
  'import':    { bg: 'rgba(107,70,193,0.12)',  text: '#6b46c1', border: 'rgba(107,70,193,0.25)' },
  'manual':    { bg: 'rgba(26,37,64,0.07)',    text: '#4a5568', border: 'rgba(26,37,64,0.15)'   },
};

export const STATUS_BADGE: Record<string, { bg: string; text: string; border: string }> = {
  'active':   { bg: 'rgba(43,108,176,0.10)',  text: '#2b6cb0', border: 'rgba(43,108,176,0.25)' },
  'new':      { bg: 'rgba(45,122,95,0.10)',   text: '#2d7a5f', border: 'rgba(45,122,95,0.25)'  },
  'replied':  { bg: 'rgba(107,70,193,0.10)',  text: '#6b46c1', border: 'rgba(107,70,193,0.25)' },
  'paused':   { bg: 'rgba(176,125,42,0.10)',  text: '#b07d2a', border: 'rgba(176,125,42,0.25)' },
  'rejected': { bg: 'rgba(192,57,43,0.10)',   text: '#c0392b', border: 'rgba(192,57,43,0.25)'  },
};
