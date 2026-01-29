import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

export const IntroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Logo animation
  const logoScale = spring({
    frame,
    fps,
    config: {
      damping: 10,
      stiffness: 100,
      mass: 0.5,
    },
  });

  const logoOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  // Tagline animation
  const taglineOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  const taglineY = interpolate(frame, [30, 50], [20, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Subtitle animation
  const subtitleOpacity = interpolate(frame, [50, 65], [0, 1], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  // Exit animation
  const exitOpacity = interpolate(frame, [75, 90], [1, 0], {
    extrapolateLeft: 'clamp',
    extrapolateRight: 'clamp',
  });

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        opacity: exitOpacity,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 24,
        }}
      >
        {/* Logo/Brand */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: 20,
            opacity: logoOpacity,
            transform: `scale(${logoScale})`,
          }}
        >
          {/* Icon */}
          <div
            style={{
              width: 100,
              height: 100,
              borderRadius: 24,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 20px 60px rgba(139, 92, 246, 0.4)',
            }}
          >
            {/* Stylized A */}
            <svg width="60" height="60" viewBox="0 0 60 60" fill="none">
              <path
                d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z"
                fill="white"
              />
            </svg>
          </div>

          {/* Text */}
          <div
            style={{
              fontSize: 80,
              fontWeight: 700,
              color: 'white',
              letterSpacing: '-2px',
            }}
          >
            Arakis
          </div>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 36,
            color: 'rgba(255, 255, 255, 0.9)',
            fontWeight: 500,
            opacity: taglineOpacity,
            transform: `translateY(${taglineY}px)`,
          }}
        >
          AI-Powered Systematic Reviews
        </div>

        {/* Subtitle */}
        <div
          style={{
            fontSize: 22,
            color: 'rgba(255, 255, 255, 0.5)',
            fontWeight: 400,
            opacity: subtitleOpacity,
          }}
        >
          From research question to publication-ready manuscript
        </div>
      </div>

      {/* Animated particles */}
      {[...Array(15)].map((_, i) => {
        const x = (i * 97) % 100;
        const y = (i * 79) % 100;
        const delay = i * 2; // Reduced delay to keep within bounds
        const fadeInEnd = Math.min(delay + 20, 60);
        const fadeOutStart = 70;
        const fadeOutEnd = 85;

        // Simple two-stage opacity: fade in then fade out
        const fadeIn = interpolate(
          frame,
          [delay, fadeInEnd],
          [0, 0.4],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        const fadeOut = interpolate(
          frame,
          [fadeOutStart, fadeOutEnd],
          [1, 0],
          { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
        );
        const particleOpacity = fadeIn * fadeOut;

        const particleY = interpolate(frame, [0, 90], [y, y - 10], {
          extrapolateRight: 'clamp',
        });

        return (
          <div
            key={i}
            style={{
              position: 'absolute',
              left: `${x}%`,
              top: `${particleY}%`,
              width: 4,
              height: 4,
              borderRadius: '50%',
              backgroundColor: '#8b5cf6',
              opacity: particleOpacity,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
