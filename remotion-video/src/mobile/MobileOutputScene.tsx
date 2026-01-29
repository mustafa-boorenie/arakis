import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

const SECTIONS = [
  { title: 'Abstract', words: 350 },
  { title: 'Introduction', words: 1200 },
  { title: 'Methods', words: 2100 },
  { title: 'Results', words: 1800 },
  { title: 'Discussion', words: 2400 },
];

const FIGURES = ['PRISMA Flow', 'Forest Plot', 'Funnel Plot'];

export const MobileOutputScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const containerScale = spring({ frame, fps, config: { damping: 12, stiffness: 80 } });
  const badgeScale = spring({ frame: frame - 20, fps, config: { damping: 8, stiffness: 100 } });
  const exitOpacity = interpolate(frame, [110, 120], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: containerOpacity * exitOpacity, padding: 24 }}>
      <div style={{ transform: `scale(${Math.min(containerScale, 1)})`, width: '100%', maxWidth: 500 }}>
        {/* Success Header */}
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 10,
              backgroundColor: '#22c55e',
              color: 'white',
              padding: '12px 24px',
              borderRadius: 12,
              fontSize: 18,
              fontWeight: 600,
              transform: `scale(${Math.max(0, Math.min(badgeScale, 1))})`,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="3">
              <polyline points="20 6 9 17 4 12" />
            </svg>
            Manuscript Ready
          </div>
        </div>

        {/* Sections */}
        <div
          style={{
            backgroundColor: 'rgba(20, 20, 30, 0.95)',
            borderRadius: 24,
            padding: 20,
            marginBottom: 20,
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <h3 style={{ color: 'white', fontSize: 16, fontWeight: 600, margin: 0, marginBottom: 16 }}>Sections</h3>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {SECTIONS.map((section, index) => {
              const sectionOpacity = interpolate(frame, [25 + index * 6, 35 + index * 6], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              });
              return (
                <div
                  key={section.title}
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    padding: '12px 14px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: 12,
                    opacity: sectionOpacity,
                  }}
                >
                  <span style={{ color: 'white', fontSize: 15, fontWeight: 500 }}>{section.title}</span>
                  <span style={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: 13 }}>~{section.words}</span>
                </div>
              );
            })}
          </div>
          <div style={{ marginTop: 16, paddingTop: 12, borderTop: '1px solid rgba(255, 255, 255, 0.1)', display: 'flex', justifyContent: 'space-between' }}>
            <span style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: 14 }}>Total</span>
            <span style={{ color: 'white', fontSize: 15, fontWeight: 600 }}>~{SECTIONS.reduce((a, b) => a + b.words, 0).toLocaleString()} words</span>
          </div>
        </div>

        {/* Figures */}
        <div
          style={{
            backgroundColor: 'rgba(20, 20, 30, 0.95)',
            borderRadius: 24,
            padding: 20,
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <h3 style={{ color: 'white', fontSize: 16, fontWeight: 600, margin: 0, marginBottom: 16 }}>Generated Figures</h3>
          <div style={{ display: 'flex', gap: 12 }}>
            {FIGURES.map((fig, index) => {
              const figOpacity = interpolate(frame, [60 + index * 8, 70 + index * 8], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              });
              const colors = ['#3b82f6', '#22c55e', '#8b5cf6'];
              return (
                <div
                  key={fig}
                  style={{
                    flex: 1,
                    padding: 14,
                    borderRadius: 14,
                    background: `linear-gradient(135deg, ${colors[index]}30, ${colors[index]}10)`,
                    border: `1px solid ${colors[index]}40`,
                    textAlign: 'center',
                    opacity: figOpacity,
                  }}
                >
                  <div
                    style={{
                      width: 40,
                      height: 40,
                      borderRadius: 10,
                      backgroundColor: colors[index],
                      margin: '0 auto 8px',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
                      <rect x="3" y="3" width="18" height="18" rx="2" />
                    </svg>
                  </div>
                  <span style={{ color: 'white', fontSize: 11, fontWeight: 500 }}>{fig}</span>
                </div>
              );
            })}
          </div>
        </div>

        {/* Export */}
        <div
          style={{
            display: 'flex',
            justifyContent: 'center',
            gap: 10,
            marginTop: 20,
            opacity: interpolate(frame, [90, 100], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }),
          }}
        >
          {['Word', 'PDF', 'LaTeX'].map((format) => (
            <div
              key={format}
              style={{
                padding: '10px 20px',
                backgroundColor: 'rgba(139, 92, 246, 0.2)',
                border: '1px solid rgba(139, 92, 246, 0.3)',
                borderRadius: 10,
                color: '#a855f7',
                fontSize: 14,
                fontWeight: 500,
              }}
            >
              {format}
            </div>
          ))}
        </div>
      </div>
    </AbsoluteFill>
  );
};
