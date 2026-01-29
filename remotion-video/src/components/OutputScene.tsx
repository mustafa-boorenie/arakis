import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

const MANUSCRIPT_SECTIONS = [
  { title: 'Abstract', words: 350 },
  { title: 'Introduction', words: 1200 },
  { title: 'Methods', words: 2100 },
  { title: 'Results', words: 1800 },
  { title: 'Discussion', words: 2400 },
  { title: 'References', words: 800 },
];

const FIGURES = [
  { title: 'PRISMA Flow Diagram', type: 'prisma' },
  { title: 'Forest Plot', type: 'forest' },
  { title: 'Funnel Plot', type: 'funnel' },
];

export const OutputScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entry animation
  const containerOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const containerScale = spring({
    frame,
    fps,
    config: { damping: 12, stiffness: 80 },
  });

  // Success badge animation
  const badgeScale = spring({
    frame: frame - 20,
    fps,
    config: { damping: 8, stiffness: 100 },
  });

  // Exit animation
  const exitOpacity = interpolate(frame, [110, 120], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        opacity: containerOpacity * exitOpacity,
      }}
    >
      <div
        style={{
          display: 'flex',
          gap: 40,
          alignItems: 'flex-start',
          transform: `scale(${Math.min(containerScale, 1)})`,
        }}
      >
        {/* Left: Manuscript preview */}
        <div
          style={{
            width: 500,
            backgroundColor: 'rgba(20, 20, 30, 0.95)',
            borderRadius: 24,
            padding: 28,
            boxShadow: '0 40px 100px rgba(0, 0, 0, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          {/* Header with success badge */}
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              marginBottom: 24,
            }}
          >
            <h2 style={{ color: 'white', fontSize: 22, fontWeight: 600, margin: 0 }}>
              Manuscript Ready
            </h2>
            <div
              style={{
                backgroundColor: '#22c55e',
                color: 'white',
                padding: '6px 12px',
                borderRadius: 8,
                fontSize: 13,
                fontWeight: 600,
                display: 'flex',
                alignItems: 'center',
                gap: 6,
                transform: `scale(${Math.max(0, Math.min(badgeScale, 1))})`,
              }}
            >
              <svg
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="3"
              >
                <polyline points="20 6 9 17 4 12" />
              </svg>
              Complete
            </div>
          </div>

          {/* Sections list */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {MANUSCRIPT_SECTIONS.map((section, index) => {
              const sectionOpacity = interpolate(
                frame,
                [30 + index * 8, 40 + index * 8],
                [0, 1],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
              );

              return (
                <div
                  key={section.title}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '12px 16px',
                    backgroundColor: 'rgba(255, 255, 255, 0.05)',
                    borderRadius: 10,
                    opacity: sectionOpacity,
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                    <svg
                      width="18"
                      height="18"
                      viewBox="0 0 24 24"
                      fill="none"
                      stroke="#8b5cf6"
                      strokeWidth="2"
                    >
                      <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                    </svg>
                    <span style={{ color: 'white', fontSize: 15, fontWeight: 500 }}>
                      {section.title}
                    </span>
                  </div>
                  <span style={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: 13 }}>
                    ~{section.words} words
                  </span>
                </div>
              );
            })}
          </div>

          {/* Total word count */}
          <div
            style={{
              marginTop: 20,
              paddingTop: 16,
              borderTop: '1px solid rgba(255, 255, 255, 0.1)',
              display: 'flex',
              justifyContent: 'space-between',
              alignItems: 'center',
            }}
          >
            <span style={{ color: 'rgba(255, 255, 255, 0.7)', fontSize: 14 }}>
              Total manuscript
            </span>
            <span style={{ color: 'white', fontSize: 16, fontWeight: 600 }}>
              ~{MANUSCRIPT_SECTIONS.reduce((a, b) => a + b.words, 0).toLocaleString()} words
            </span>
          </div>
        </div>

        {/* Right: Figures */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          <h3 style={{ color: 'white', fontSize: 18, fontWeight: 600, margin: 0 }}>
            Generated Figures
          </h3>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            {FIGURES.map((figure, index) => {
              const figureOpacity = interpolate(
                frame,
                [50 + index * 10, 60 + index * 10],
                [0, 1],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
              );

              const figureScale = spring({
                frame: frame - (50 + index * 10),
                fps,
                config: { damping: 10, stiffness: 80 },
              });

              // Figure-specific gradient
              const gradients: Record<string, string> = {
                prisma: 'linear-gradient(135deg, #3b82f6 0%, #1d4ed8 100%)',
                forest: 'linear-gradient(135deg, #22c55e 0%, #15803d 100%)',
                funnel: 'linear-gradient(135deg, #8b5cf6 0%, #6d28d9 100%)',
              };

              return (
                <div
                  key={figure.type}
                  style={{
                    width: 300,
                    height: 100,
                    backgroundColor: 'rgba(20, 20, 30, 0.95)',
                    borderRadius: 16,
                    padding: 16,
                    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    gap: 16,
                    opacity: figureOpacity,
                    transform: `scale(${Math.min(figureScale, 1)})`,
                  }}
                >
                  {/* Figure preview */}
                  <div
                    style={{
                      width: 70,
                      height: 70,
                      borderRadius: 12,
                      background: gradients[figure.type],
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                    }}
                  >
                    {figure.type === 'prisma' && (
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="white">
                        <rect x="7" y="2" width="10" height="4" rx="1" />
                        <rect x="4" y="10" width="6" height="4" rx="1" />
                        <rect x="14" y="10" width="6" height="4" rx="1" />
                        <rect x="9" y="18" width="6" height="4" rx="1" />
                        <path d="M12 6v4M9 14v4M15 14l-3 4" stroke="white" strokeWidth="1.5" />
                      </svg>
                    )}
                    {figure.type === 'forest' && (
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                        <line x1="4" y1="6" x2="20" y2="6" stroke="white" strokeWidth="1.5" />
                        <line x1="4" y1="12" x2="20" y2="12" stroke="white" strokeWidth="1.5" />
                        <line x1="4" y1="18" x2="20" y2="18" stroke="white" strokeWidth="1.5" />
                        <rect x="8" y="4" width="4" height="4" fill="white" />
                        <rect x="10" y="10" width="6" height="4" fill="white" />
                        <rect x="6" y="16" width="8" height="4" fill="white" />
                        <path d="M12 2v20" stroke="white" strokeWidth="2" strokeDasharray="2 2" />
                      </svg>
                    )}
                    {figure.type === 'funnel' && (
                      <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
                        <path d="M4 4h16l-6 16h-4L4 4z" stroke="white" strokeWidth="1.5" />
                        <circle cx="8" cy="8" r="2" fill="white" />
                        <circle cx="16" cy="8" r="2" fill="white" />
                        <circle cx="10" cy="12" r="2" fill="white" />
                        <circle cx="14" cy="12" r="2" fill="white" />
                        <circle cx="12" cy="16" r="2" fill="white" />
                      </svg>
                    )}
                  </div>

                  <div>
                    <p style={{ color: 'white', fontSize: 15, fontWeight: 500, margin: 0 }}>
                      {figure.title}
                    </p>
                    <p
                      style={{
                        color: 'rgba(255, 255, 255, 0.5)',
                        fontSize: 13,
                        margin: 0,
                        marginTop: 4,
                      }}
                    >
                      300 DPI • PNG
                    </p>
                  </div>
                </div>
              );
            })}
          </div>

          {/* Export options */}
          <div
            style={{
              display: 'flex',
              gap: 12,
              marginTop: 16,
              opacity: interpolate(frame, [90, 100], [0, 1], {
                extrapolateLeft: 'clamp',
                extrapolateRight: 'clamp',
              }),
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
                Export {format}
              </div>
            ))}
          </div>
        </div>
      </div>
    </AbsoluteFill>
  );
};
