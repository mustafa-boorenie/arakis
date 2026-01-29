import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

// The 12 workflow stages
const STAGES = [
  { key: 'search', label: 'Searching databases', icon: 'M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z', color: '#8b5cf6' },
  { key: 'screen', label: 'Screening papers', icon: 'M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z', color: '#a855f7' },
  { key: 'pdf_fetch', label: 'Fetching PDFs', icon: 'M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4', color: '#7c3aed' },
  { key: 'extract', label: 'Extracting data', icon: 'M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2', color: '#6366f1' },
  { key: 'rob', label: 'Risk of Bias', icon: 'M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z', color: '#4f46e5' },
  { key: 'analysis', label: 'Meta-analysis', icon: 'M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z', color: '#22c55e' },
  { key: 'prisma', label: 'PRISMA diagram', icon: 'M4 5a1 1 0 011-1h14a1 1 0 011 1v2a1 1 0 01-1 1H5a1 1 0 01-1-1V5zM4 13a1 1 0 011-1h6a1 1 0 011 1v6a1 1 0 01-1 1H5a1 1 0 01-1-1v-6zM16 13a1 1 0 011-1h2a1 1 0 011 1v6a1 1 0 01-1 1h-2a1 1 0 01-1-1v-6z', color: '#3b82f6' },
  { key: 'tables', label: 'Generating tables', icon: 'M3 10h18M3 14h18m-9-4v8m-7 0h14a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z', color: '#0ea5e9' },
  { key: 'introduction', label: 'Writing introduction', icon: 'M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253', color: '#14b8a6' },
  { key: 'methods', label: 'Writing methods', icon: 'M10 20l4-16m4 4l4 4-4 4M6 16l-4-4 4-4', color: '#f59e0b' },
  { key: 'results', label: 'Writing results', icon: 'M7 12l3-3 3 3 4-4M8 21l4-4 4 4M3 4h18M4 4h16v12a1 1 0 01-1 1H5a1 1 0 01-1-1V4z', color: '#ef4444' },
  { key: 'discussion', label: 'Writing discussion', icon: 'M8 12h.01M12 12h.01M16 12h.01M21 12c0 4.418-4.03 8-9 8a9.863 9.863 0 01-4.255-.949L3 20l1.395-3.72C3.512 15.042 3 13.574 3 12c0-4.418 4.03-8 9-8s9 3.582 9 8z', color: '#ec4899' },
];

// Stats animation
const STATS = [
  { label: 'Found', values: [0, 847, 847, 847, 847, 847, 847, 847, 847, 847, 847, 847] },
  { label: 'Screened', values: [0, 0, 312, 312, 312, 312, 312, 312, 312, 312, 312, 312] },
  { label: 'Included', values: [0, 0, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24] },
];

export const WorkflowScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entry animation
  const containerOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // Calculate which stage is active
  const stageFrameDuration = 35; // frames per stage
  const currentStageIndex = Math.min(
    Math.floor(frame / stageFrameDuration),
    STAGES.length - 1
  );

  // Progress percentage
  const progress = interpolate(
    frame,
    [0, STAGES.length * stageFrameDuration],
    [0, 100],
    { extrapolateRight: 'clamp' }
  );

  // Current stat values
  const currentStats = STATS.map((stat) => {
    const idx = Math.min(currentStageIndex, stat.values.length - 1);
    return {
      label: stat.label,
      value: stat.values[idx],
    };
  });

  // Exit animation
  const exitOpacity = interpolate(frame, [440, 450], [1, 0], {
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
          gap: 60,
          alignItems: 'flex-start',
        }}
      >
        {/* Left: Stage list */}
        <div
          style={{
            width: 400,
            backgroundColor: 'rgba(20, 20, 30, 0.95)',
            borderRadius: 24,
            padding: 24,
            boxShadow: '0 40px 100px rgba(0, 0, 0, 0.5)',
            border: '1px solid rgba(255, 255, 255, 0.1)',
          }}
        >
          <h3
            style={{
              color: 'white',
              fontSize: 20,
              fontWeight: 600,
              marginBottom: 20,
              margin: 0,
              marginBottom: 20,
            }}
          >
            Workflow Progress
          </h3>

          {/* Progress bar */}
          <div
            style={{
              height: 8,
              backgroundColor: 'rgba(255, 255, 255, 0.1)',
              borderRadius: 4,
              marginBottom: 24,
              overflow: 'hidden',
            }}
          >
            <div
              style={{
                height: '100%',
                width: `${progress}%`,
                background: 'linear-gradient(90deg, #8b5cf6 0%, #22c55e 100%)',
                borderRadius: 4,
                transition: 'width 0.3s ease',
              }}
            />
          </div>

          {/* Stages */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {STAGES.map((stage, index) => {
              const isCompleted = index < currentStageIndex;
              const isActive = index === currentStageIndex;
              const isPending = index > currentStageIndex;

              // Staggered animation
              const stageOpacity = interpolate(
                frame,
                [index * 3, index * 3 + 15],
                [0, 1],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
              );

              return (
                <div
                  key={stage.key}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 12,
                    padding: '10px 12px',
                    borderRadius: 12,
                    backgroundColor: isActive
                      ? 'rgba(139, 92, 246, 0.2)'
                      : 'transparent',
                    opacity: stageOpacity,
                  }}
                >
                  {/* Icon container */}
                  <div
                    style={{
                      width: 32,
                      height: 32,
                      borderRadius: 8,
                      backgroundColor: isCompleted
                        ? '#22c55e'
                        : isActive
                          ? stage.color
                          : 'rgba(255, 255, 255, 0.1)',
                      display: 'flex',
                      alignItems: 'center',
                      justifyContent: 'center',
                      flexShrink: 0,
                    }}
                  >
                    {isCompleted ? (
                      // Checkmark
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="white"
                        strokeWidth="3"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <polyline points="20 6 9 17 4 12" />
                      </svg>
                    ) : isActive ? (
                      // Spinner
                      <div
                        style={{
                          width: 16,
                          height: 16,
                          border: '2px solid rgba(255, 255, 255, 0.3)',
                          borderTopColor: 'white',
                          borderRadius: '50%',
                          animation: 'spin 1s linear infinite',
                        }}
                      />
                    ) : (
                      // Stage icon
                      <svg
                        width="16"
                        height="16"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="rgba(255, 255, 255, 0.5)"
                        strokeWidth="2"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                      >
                        <path d={stage.icon} />
                      </svg>
                    )}
                  </div>

                  {/* Label */}
                  <span
                    style={{
                      color: isActive
                        ? 'white'
                        : isCompleted
                          ? '#22c55e'
                          : 'rgba(255, 255, 255, 0.5)',
                      fontSize: 14,
                      fontWeight: isActive ? 600 : 400,
                    }}
                  >
                    {stage.label}
                  </span>

                  {/* Badge */}
                  {isActive && (
                    <span
                      style={{
                        marginLeft: 'auto',
                        backgroundColor: 'rgba(139, 92, 246, 0.3)',
                        color: '#a855f7',
                        padding: '2px 8px',
                        borderRadius: 6,
                        fontSize: 11,
                        fontWeight: 600,
                      }}
                    >
                      In Progress
                    </span>
                  )}
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Stats and visualization */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
          {/* Stats cards */}
          <div style={{ display: 'flex', gap: 20 }}>
            {currentStats.map((stat, index) => {
              const cardOpacity = interpolate(
                frame,
                [10 + index * 10, 20 + index * 10],
                [0, 1],
                { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
              );

              const statScale = spring({
                frame: frame - (10 + index * 10),
                fps,
                config: { damping: 10, stiffness: 100 },
              });

              return (
                <div
                  key={stat.label}
                  style={{
                    width: 140,
                    backgroundColor: 'rgba(20, 20, 30, 0.95)',
                    borderRadius: 16,
                    padding: 20,
                    textAlign: 'center',
                    boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
                    border: '1px solid rgba(255, 255, 255, 0.1)',
                    opacity: cardOpacity,
                    transform: `scale(${Math.min(statScale, 1)})`,
                  }}
                >
                  <p
                    style={{
                      fontSize: 36,
                      fontWeight: 700,
                      color: 'white',
                      margin: 0,
                    }}
                  >
                    {stat.value}
                  </p>
                  <p
                    style={{
                      fontSize: 14,
                      color: 'rgba(255, 255, 255, 0.5)',
                      margin: 0,
                      marginTop: 4,
                    }}
                  >
                    {stat.label}
                  </p>
                </div>
              );
            })}
          </div>

          {/* Current stage visualization */}
          <div
            style={{
              width: 480,
              height: 320,
              backgroundColor: 'rgba(20, 20, 30, 0.95)',
              borderRadius: 24,
              padding: 24,
              boxShadow: '0 40px 100px rgba(0, 0, 0, 0.5)',
              border: '1px solid rgba(255, 255, 255, 0.1)',
              display: 'flex',
              flexDirection: 'column',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            {/* Current stage indicator */}
            <div
              style={{
                width: 80,
                height: 80,
                borderRadius: 20,
                backgroundColor: STAGES[currentStageIndex].color,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 24,
                boxShadow: `0 20px 60px ${STAGES[currentStageIndex].color}40`,
              }}
            >
              <svg
                width="40"
                height="40"
                viewBox="0 0 24 24"
                fill="none"
                stroke="white"
                strokeWidth="2"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d={STAGES[currentStageIndex].icon} />
              </svg>
            </div>

            <h2
              style={{
                color: 'white',
                fontSize: 28,
                fontWeight: 600,
                margin: 0,
                marginBottom: 8,
              }}
            >
              {STAGES[currentStageIndex].label}
            </h2>

            <p
              style={{
                color: 'rgba(255, 255, 255, 0.5)',
                fontSize: 16,
                margin: 0,
                marginBottom: 24,
              }}
            >
              Stage {currentStageIndex + 1} of {STAGES.length}
            </p>

            {/* Animated progress dots */}
            <div style={{ display: 'flex', gap: 8 }}>
              {[0, 1, 2].map((dot) => {
                const dotOpacity = interpolate(
                  (frame + dot * 10) % 30,
                  [0, 15, 30],
                  [0.3, 1, 0.3]
                );
                return (
                  <div
                    key={dot}
                    style={{
                      width: 10,
                      height: 10,
                      borderRadius: '50%',
                      backgroundColor: STAGES[currentStageIndex].color,
                      opacity: dotOpacity,
                    }}
                  />
                );
              })}
            </div>
          </div>

          {/* Cost tracker */}
          <div
            style={{
              textAlign: 'center',
              color: 'rgba(255, 255, 255, 0.5)',
              fontSize: 14,
            }}
          >
            Estimated cost: ${((currentStageIndex + 1) * 0.42).toFixed(2)}
          </div>
        </div>
      </div>

      {/* CSS for spinner animation */}
      <style>
        {`
          @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
          }
        `}
      </style>
    </AbsoluteFill>
  );
};
