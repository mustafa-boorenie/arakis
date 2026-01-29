import {
  AbsoluteFill,
  useCurrentFrame,
  useVideoConfig,
  interpolate,
  spring,
} from 'remotion';

export const OutroScene: React.FC = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Entry animation
  const contentOpacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: 'clamp',
  });

  const contentScale = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 100 },
  });

  // Stats animation
  const stats = [
    { value: '12', label: 'Automated Stages' },
    { value: '~5min', label: 'Average Time' },
    { value: '$5', label: 'Average Cost' },
  ];

  return (
    <AbsoluteFill
      style={{
        justifyContent: 'center',
        alignItems: 'center',
        opacity: contentOpacity,
      }}
    >
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          gap: 40,
          transform: `scale(${Math.min(contentScale, 1)})`,
        }}
      >
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 16 }}>
          <div
            style={{
              width: 60,
              height: 60,
              borderRadius: 16,
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              boxShadow: '0 20px 60px rgba(139, 92, 246, 0.4)',
            }}
          >
            <svg width="36" height="36" viewBox="0 0 60 60" fill="none">
              <path
                d="M30 8L8 52H18L22 44H38L42 52H52L30 8ZM26 36L30 24L34 36H26Z"
                fill="white"
              />
            </svg>
          </div>
          <span
            style={{
              fontSize: 48,
              fontWeight: 700,
              color: 'white',
              letterSpacing: '-1px',
            }}
          >
            Arakis
          </span>
        </div>

        {/* Tagline */}
        <div
          style={{
            fontSize: 28,
            color: 'rgba(255, 255, 255, 0.8)',
            fontWeight: 500,
            textAlign: 'center',
          }}
        >
          Systematic reviews, automated.
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', gap: 60, marginTop: 20 }}>
          {stats.map((stat, index) => {
            const statOpacity = interpolate(
              frame,
              [20 + index * 8, 30 + index * 8],
              [0, 1],
              { extrapolateLeft: 'clamp', extrapolateRight: 'clamp' }
            );

            return (
              <div
                key={stat.label}
                style={{
                  textAlign: 'center',
                  opacity: statOpacity,
                }}
              >
                <p
                  style={{
                    fontSize: 42,
                    fontWeight: 700,
                    color: '#8b5cf6',
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
                    marginTop: 8,
                  }}
                >
                  {stat.label}
                </p>
              </div>
            );
          })}
        </div>

        {/* CTA */}
        <div
          style={{
            marginTop: 20,
            opacity: interpolate(frame, [45, 55], [0, 1], {
              extrapolateLeft: 'clamp',
              extrapolateRight: 'clamp',
            }),
          }}
        >
          <div
            style={{
              padding: '16px 48px',
              background: 'linear-gradient(135deg, #8b5cf6 0%, #a855f7 100%)',
              borderRadius: 14,
              fontSize: 20,
              fontWeight: 600,
              color: 'white',
              boxShadow: '0 20px 60px rgba(139, 92, 246, 0.4)',
            }}
          >
            Try Arakis Today
          </div>
        </div>
      </div>

      {/* Animated gradient orbs */}
      <div
        style={{
          position: 'absolute',
          top: '20%',
          left: '10%',
          width: 300,
          height: 300,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(139, 92, 246, 0.2) 0%, transparent 70%)',
          filter: 'blur(60px)',
          animation: 'float 6s ease-in-out infinite',
        }}
      />
      <div
        style={{
          position: 'absolute',
          bottom: '20%',
          right: '10%',
          width: 250,
          height: 250,
          borderRadius: '50%',
          background: 'radial-gradient(circle, rgba(168, 85, 247, 0.2) 0%, transparent 70%)',
          filter: 'blur(60px)',
          animation: 'float 8s ease-in-out infinite reverse',
        }}
      />

      <style>
        {`
          @keyframes float {
            0%, 100% { transform: translateY(0px); }
            50% { transform: translateY(-20px); }
          }
        `}
      </style>
    </AbsoluteFill>
  );
};
