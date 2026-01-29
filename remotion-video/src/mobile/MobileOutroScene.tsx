import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

export const MobileOutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const contentOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const contentScale = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });

  const stats = [
    { value: '12', label: 'Stages' },
    { value: '~5min', label: 'Time' },
    { value: '$5', label: 'Cost' },
  ];

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: contentOpacity, padding: 32 }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 40, transform: `scale(${Math.min(contentScale, 1)})` }}>
        {/* Logo */}
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 80,
              height: 80,
              borderRadius: 22,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 30px 80px rgba(139, 92, 246, 0.5)',
            }}
          >
            <svg width="48" height="48" viewBox="0 0 60 60" fill="white">
              <path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" />
            </svg>
          </div>
          <span style={{ fontSize: 56, fontWeight: 700, color: 'white' }}>Arakis</span>
        </div>

        {/* Tagline */}
        <div style={{ fontSize: 26, color: 'rgba(255, 255, 255, 0.8)', fontWeight: 500, textAlign: 'center' }}>
          Systematic reviews,
          <br />
          <span style={{ color: '#a855f7' }}>automated.</span>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 32 }}>
          {stats.map((stat, index) => {
            const statOpacity = interpolate(frame, [20 + index * 6, 30 + index * 6], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            });
            return (
              <div key={stat.label} style={{ textAlign: 'center', opacity: statOpacity }}>
                <p style={{ fontSize: 36, fontWeight: 700, color: '#8b5cf6', margin: 0 }}>{stat.value}</p>
                <p style={{ fontSize: 14, color: 'rgba(255, 255, 255, 0.5)', margin: 0, marginTop: 4 }}>{stat.label}</p>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div
          style={{
            padding: '20px 56px',
            background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
            borderRadius: 16,
            fontSize: 22,
            fontWeight: 700,
            color: 'white',
            boxShadow: '0 20px 60px rgba(139, 92, 246, 0.4)',
            opacity: interpolate(frame, [40, 50], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          Try Arakis Today
        </div>
      </div>
    </AbsoluteFill>
  );
};
