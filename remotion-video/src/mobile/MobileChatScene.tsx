import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

const RESEARCH_QUESTION = 'Effect of aspirin on sepsis mortality';
const INCLUSION_CRITERIA = 'RCTs, Adults, Aspirin, Mortality';
const EXCLUSION_CRITERIA = 'Pediatric, Animal studies';

export const MobileChatScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const containerOpacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: 'clamp' });
  const containerScale = spring({ frame, fps, config: { damping: 15, stiffness: 100 } });

  const msg1Opacity = interpolate(frame, [15, 25], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const questionProgress = interpolate(frame, [30, 60], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const questionText = RESEARCH_QUESTION.slice(0, Math.floor(RESEARCH_QUESTION.length * questionProgress));

  const msg2Opacity = interpolate(frame, [70, 80], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const inclusionProgress = interpolate(frame, [85, 110], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const inclusionText = INCLUSION_CRITERIA.slice(0, Math.floor(INCLUSION_CRITERIA.length * inclusionProgress));

  const msg3Opacity = interpolate(frame, [115, 125], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const exclusionProgress = interpolate(frame, [130, 150], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const exclusionText = EXCLUSION_CRITERIA.slice(0, Math.floor(EXCLUSION_CRITERIA.length * exclusionProgress));

  const buttonOpacity = interpolate(frame, [155, 165], [0, 1], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });
  const buttonScale = spring({ frame: frame - 155, fps, config: { damping: 8, stiffness: 100 } });
  const exitOpacity = interpolate(frame, [170, 180], [1, 0], { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' });

  return (
    <AbsoluteFill style={{ justifyContent: 'center', alignItems: 'center', opacity: containerOpacity * exitOpacity, padding: 24 }}>
      <div
        style={{
          width: '100%',
          maxWidth: 500,
          backgroundColor: 'rgba(20, 20, 30, 0.95)',
          borderRadius: 32,
          padding: 28,
          boxShadow: '0 40px 100px rgba(0, 0, 0, 0.5)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          transform: `scale(${Math.min(containerScale, 1)})`,
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 28 }}>
          <div
            style={{
              width: 48,
              height: 48,
              borderRadius: 14,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="28" height="28" viewBox="0 0 60 60" fill="white">
              <path d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z" />
            </svg>
          </div>
          <span style={{ color: 'white', fontSize: 22, fontWeight: 600 }}>New Review</span>
        </div>

        {/* Messages */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          <div style={{ opacity: msg1Opacity }}>
            <div style={{ backgroundColor: 'rgba(139, 92, 246, 0.2)', padding: 14, borderRadius: 16, borderTopLeftRadius: 4 }}>
              <p style={{ color: 'white', margin: 0, fontSize: 16 }}>Research question?</p>
            </div>
          </div>

          {questionProgress > 0 && (
            <div style={{ alignSelf: 'flex-end' }}>
              <div style={{ backgroundColor: '#8b5cf6', padding: 14, borderRadius: 16, borderTopRightRadius: 4 }}>
                <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                  {questionText}{questionProgress < 1 && <span style={{ opacity: frame % 15 < 8 ? 1 : 0 }}>|</span>}
                </p>
              </div>
            </div>
          )}

          <div style={{ opacity: msg2Opacity }}>
            <div style={{ backgroundColor: 'rgba(139, 92, 246, 0.2)', padding: 14, borderRadius: 16, borderTopLeftRadius: 4 }}>
              <p style={{ color: 'white', margin: 0, fontSize: 16 }}>Inclusion criteria?</p>
            </div>
          </div>

          {inclusionProgress > 0 && (
            <div style={{ alignSelf: 'flex-end' }}>
              <div style={{ backgroundColor: '#8b5cf6', padding: 14, borderRadius: 16, borderTopRightRadius: 4 }}>
                <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                  {inclusionText}{inclusionProgress < 1 && <span style={{ opacity: frame % 15 < 8 ? 1 : 0 }}>|</span>}
                </p>
              </div>
            </div>
          )}

          <div style={{ opacity: msg3Opacity }}>
            <div style={{ backgroundColor: 'rgba(139, 92, 246, 0.2)', padding: 14, borderRadius: 16, borderTopLeftRadius: 4 }}>
              <p style={{ color: 'white', margin: 0, fontSize: 16 }}>Exclusion criteria?</p>
            </div>
          </div>

          {exclusionProgress > 0 && (
            <div style={{ alignSelf: 'flex-end' }}>
              <div style={{ backgroundColor: '#8b5cf6', padding: 14, borderRadius: 16, borderTopRightRadius: 4 }}>
                <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                  {exclusionText}{exclusionProgress < 1 && <span style={{ opacity: frame % 15 < 8 ? 1 : 0 }}>|</span>}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Button */}
        <div style={{ marginTop: 24, opacity: buttonOpacity, transform: `scale(${Math.max(0, Math.min(buttonScale, 1.1))})` }}>
          <button
            style={{
              width: '100%',
              padding: '18px 32px',
              backgroundColor: '#8b5cf6',
              color: 'white',
              border: 'none',
              borderRadius: 14,
              fontSize: 18,
              fontWeight: 600,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 10,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white"><path d="M8 5v14l11-7z" /></svg>
            Start Review
          </button>
        </div>
      </div>
    </AbsoluteFill>
  );
};
