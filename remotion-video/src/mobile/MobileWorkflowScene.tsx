import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

const STAGES = [
  { key: 'search', label: 'Searching', color: '#8b5cf6' },
  { key: 'screen', label: 'Screening', color: '#a855f7' },
  { key: 'pdf_fetch', label: 'Fetching PDFs', color: '#7c3aed' },
  { key: 'extract', label: 'Extracting', color: '#6366f1' },
  { key: 'rob', label: 'Risk of Bias', color: '#4f46e5' },
  { key: 'analysis', label: 'Meta-analysis', color: '#22c55e' },
  { key: 'prisma', label: 'PRISMA', color: '#3b82f6' },
  { key: 'tables', label: 'Tables', color: '#0ea5e9' },
  { key: 'introduction', label: 'Introduction', color: '#14b8a6' },
  { key: 'methods', label: 'Methods', color: '#f59e0b' },
  { key: 'results', label: 'Results', color: '#ef4444' },
  { key: 'discussion', label: 'Discussion', color: '#ec4899' },
];

const STATS = [
  { label: 'Found', values: [0, 847, 847, 847, 847, 847, 847, 847, 847, 847, 847, 847] },
  { label: 'Screened', values: [0, 0, 312, 312, 312, 312, 312, 312, 312, 312, 312, 312] },
  { label: 'Included', values: [0, 0, 0, 24, 24, 24, 24, 24, 24, 24, 24, 24] },
];

export const MobileWorkflowScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const stageFrameDuration = 35;
  const currentStageIndex = Math.min(Math.floor(frame / stageFrameDuration), STAGES.length - 1);
  const progress = interpolate(frame, [0, STAGES.length * stageFrameDuration], [0, 100], { extrapolateRight: 'clamp' });

  const currentStats = STATS.map((stat) => ({
    label: stat.label,
    value: stat.values[Math.min(currentStageIndex, stat.values.length - 1)],
  }));

  const exitOpacity = interpolate(frame, [440, 450], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'flex-start', alignItems: 'center', opacity: containerOpacity * exitOpacity, padding: 24, paddingTop: 60 }}>
      {/* Current Stage Highlight */}
      <div
        style={{
          width: 100,
          height: 100,
          borderRadius: 28,
          backgroundColor: STAGES[currentStageIndex].color,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          marginBottom: 20,
          boxShadow: `0 20px 60px ${STAGES[currentStageIndex].color}60`,
        }}
      >
        <span style={{ fontSize: 40, color: 'white', fontWeight: 700 }}>{currentStageIndex + 1}</span>
      </div>

      <h2 style={{ color: 'white', fontSize: 28, fontWeight: 600, margin: 0, marginBottom: 8, textAlign: 'center' }}>
        {STAGES[currentStageIndex].label}
      </h2>
      <p style={{ color: 'rgba(255, 255, 255, 0.5)', fontSize: 16, margin: 0, marginBottom: 32 }}>
        Stage {currentStageIndex + 1} of {STAGES.length}
      </p>

      {/* Progress bar */}
      <div style={{ width: '100%', maxWidth: 400, marginBottom: 32 }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
          <span style={{ color: 'rgba(255, 255, 255, 0.6)', fontSize: 14 }}>Progress</span>
          <span style={{ color: 'white', fontSize: 14, fontWeight: 600 }}>{Math.round(progress)}%</span>
        </div>
        <div style={{ height: 10, backgroundColor: 'rgba(255, 255, 255, 0.1)', borderRadius: 5, overflow: 'hidden' }}>
          <div
            style={{
              height: '100%',
              width: `${progress}%`,
              background: 'linear-gradient(90deg, #8b5cf6 0%, #22c55e 100%)',
              borderRadius: 5,
            }}
          />
        </div>
      </div>

      {/* Stats */}
      <div style={{ display: 'flex', gap: 16, marginBottom: 32 }}>
        {currentStats.map((stat, i) => {
          const statOpacity = interpolate(frame, [10 + i * 8, 20 + i * 8], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
          return (
            <div
              key={stat.label}
              style={{
                width: 100,
                backgroundColor: 'rgba(20, 20, 30, 0.95)',
                borderRadius: 16,
                padding: 16,
                textAlign: 'center',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                opacity: statOpacity,
              }}
            >
              <p style={{ fontSize: 28, fontWeight: 700, color: 'white', margin: 0 }}>{stat.value}</p>
              <p style={{ fontSize: 12, color: 'rgba(255, 255, 255, 0.5)', margin: 0, marginTop: 4 }}>{stat.label}</p>
            </div>
          );
        })}
      </div>

      {/* Stage list */}
      <div
        style={{
          width: '100%',
          maxWidth: 400,
          backgroundColor: 'rgba(20, 20, 30, 0.95)',
          borderRadius: 24,
          padding: 20,
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }}
      >
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
          {STAGES.map((stage, index) => {
            const isCompleted = index < currentStageIndex;
            const isActive = index === currentStageIndex;
            const stageOpacity = interpolate(frame, [index * 2, index * 2 + 10], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

            return (
              <div
                key={stage.key}
                style={{
                  padding: '10px 8px',
                  borderRadius: 10,
                  backgroundColor: isActive ? 'rgba(139, 92, 246, 0.2)' : 'transparent',
                  opacity: stageOpacity,
                  textAlign: 'center',
                }}
              >
                <div
                  style={{
                    width: 28,
                    height: 28,
                    borderRadius: 8,
                    backgroundColor: isCompleted ? '#22c55e' : isActive ? stage.color : 'rgba(255, 255, 255, 0.1)',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 6px',
                  }}
                >
                  {isCompleted ? (
                    <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="white" strokeWidth="3"><polyline points="20 6 9 17 4 12" /></svg>
                  ) : isActive ? (
                    <div style={{ width: 12, height: 12, border: '2px solid white', borderTopColor: 'transparent', borderRadius: '50%' }} />
                  ) : (
                    <span style={{ fontSize: 12, color: 'rgba(255, 255, 255, 0.5)' }}>{index + 1}</span>
                  )}
                </div>
                <span style={{ fontSize: 10, color: isActive ? 'white' : isCompleted ? '#22c55e' : 'rgba(255, 255, 255, 0.5)' }}>
                  {stage.label}
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <style>{`@keyframes spin { from { transform: rotate(0deg); } to { transform: rotate(360deg); } }`}</style>
    </AbsoluteFill>
  );
};
