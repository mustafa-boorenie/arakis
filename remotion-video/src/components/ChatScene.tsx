import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

const RESEARCH_QUESTION = 'Effect of aspirin on sepsis mortality in adult patients';
const INCLUSION_CRITERIA = 'RCTs, Adults with sepsis, Aspirin intervention, Mortality outcome';
const EXCLUSION_CRITERIA = 'Pediatric studies, Animal studies, Non-English';

export const ChatScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Container entry
  const containerOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const containerScale = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 100 },
  });

  // Message 1: Research question prompt
  const msg1Opacity = interpolate(frame, [15, 25], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // User typing research question
  const questionProgress = interpolate(frame, [30, 70], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const questionText = RESEARCH_QUESTION.slice(
    0,
    Math.floor(RESEARCH_QUESTION.length * questionProgress)
  );

  // Message 2: Inclusion prompt
  const msg2Opacity = interpolate(frame, [80, 90], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Inclusion criteria typing
  const inclusionProgress = interpolate(frame, [95, 125], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const inclusionText = INCLUSION_CRITERIA.slice(
    0,
    Math.floor(INCLUSION_CRITERIA.length * inclusionProgress)
  );

  // Message 3: Exclusion prompt
  const msg3Opacity = interpolate(frame, [130, 140], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Exclusion criteria typing
  const exclusionProgress = interpolate(frame, [145, 165], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });
  const exclusionText = EXCLUSION_CRITERIA.slice(
    0,
    Math.floor(EXCLUSION_CRITERIA.length * exclusionProgress)
  );

  // Start button animation
  const buttonOpacity = interpolate(frame, [170, 175], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const buttonScale = spring({
    frame: frame - 170,
    fps,
    config: { damping: 8, stiffness: 100 },
  });

  // Exit animation
  const exitOpacity = interpolate(frame, [175, 180], [1, 0], {
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
      {/* Chat container */}
      <div
        style={{
          width: 800,
          backgroundColor: 'rgba(20, 20, 30, 0.95)',
          borderRadius: 24,
          padding: 32,
          boxShadow: '0 40px 100px rgba(0, 0, 0, 0.5)',
          border: '1px solid rgba(255, 255, 255, 0.1)',
          transform: `scale(${Math.min(containerScale, 1)})`,
        }}
      >
        {/* Header */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 12,
            marginBottom: 32,
          }}
        >
          <div
            style={{
              width: 40,
              height: 40,
              borderRadius: 10,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
            }}
          >
            <svg width="24" height="24" viewBox="0 0 24 24" fill="white">
              <path d="M12 3L2 21H22L12 3ZM10.5 16.5L12 10.5L13.5 16.5H10.5Z" />
            </svg>
          </div>
          <span style={{ color: 'white', fontSize: 20, fontWeight: 600 }}>
            New Systematic Review
          </span>
        </div>

        {/* Messages */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
          {/* AI Message 1 */}
          <div style={{ opacity: msg1Opacity }}>
            <div
              style={{
                backgroundColor: 'rgba(139, 92, 246, 0.2)',
                padding: 16,
                borderRadius: 16,
                borderTopLeftRadius: 4,
                maxWidth: '80%',
              }}
            >
              <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                What's your research question?
              </p>
            </div>
          </div>

          {/* User response 1 */}
          {questionProgress > 0 && (
            <div style={{ alignSelf: 'flex-end' }}>
              <div
                style={{
                  backgroundColor: '#8b5cf6',
                  padding: 16,
                  borderRadius: 16,
                  borderTopRightRadius: 4,
                  maxWidth: '80%',
                }}
              >
                <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                  {questionText}
                  {questionProgress < 1 && (
                    <span style={{ opacity: frame % 15 < 8 ? 1 : 0 }}>|</span>
                  )}
                </p>
              </div>
            </div>
          )}

          {/* AI Message 2 */}
          <div style={{ opacity: msg2Opacity }}>
            <div
              style={{
                backgroundColor: 'rgba(139, 92, 246, 0.2)',
                padding: 16,
                borderRadius: 16,
                borderTopLeftRadius: 4,
                maxWidth: '80%',
              }}
            >
              <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                What are your inclusion criteria?
              </p>
            </div>
          </div>

          {/* User response 2 */}
          {inclusionProgress > 0 && (
            <div style={{ alignSelf: 'flex-end' }}>
              <div
                style={{
                  backgroundColor: '#8b5cf6',
                  padding: 16,
                  borderRadius: 16,
                  borderTopRightRadius: 4,
                  maxWidth: '80%',
                }}
              >
                <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                  {inclusionText}
                  {inclusionProgress < 1 && (
                    <span style={{ opacity: frame % 15 < 8 ? 1 : 0 }}>|</span>
                  )}
                </p>
              </div>
            </div>
          )}

          {/* AI Message 3 */}
          <div style={{ opacity: msg3Opacity }}>
            <div
              style={{
                backgroundColor: 'rgba(139, 92, 246, 0.2)',
                padding: 16,
                borderRadius: 16,
                borderTopLeftRadius: 4,
                maxWidth: '80%',
              }}
            >
              <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                Any exclusion criteria?
              </p>
            </div>
          </div>

          {/* User response 3 */}
          {exclusionProgress > 0 && (
            <div style={{ alignSelf: 'flex-end' }}>
              <div
                style={{
                  backgroundColor: '#8b5cf6',
                  padding: 16,
                  borderRadius: 16,
                  borderTopRightRadius: 4,
                  maxWidth: '80%',
                }}
              >
                <p style={{ color: 'white', margin: 0, fontSize: 16 }}>
                  {exclusionText}
                  {exclusionProgress < 1 && (
                    <span style={{ opacity: frame % 15 < 8 ? 1 : 0 }}>|</span>
                  )}
                </p>
              </div>
            </div>
          )}
        </div>

        {/* Start Button */}
        <div
          style={{
            marginTop: 24,
            opacity: buttonOpacity,
            transform: `scale(${Math.max(0, Math.min(buttonScale, 1.1))})`,
          }}
        >
          <button
            style={{
              width: '100%',
              padding: '16px 32px',
              backgroundColor: '#8b5cf6',
              color: 'white',
              border: 'none',
              borderRadius: 12,
              fontSize: 18,
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: 8,
            }}
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="white">
              <path d="M8 5v14l11-7z" />
            </svg>
            Start Systematic Review
          </button>
        </div>
      </div>
    </AbsoluteFill>
  );
};
