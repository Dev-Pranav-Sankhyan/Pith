import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Audio,
  staticFile,
} from "remotion";

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
}

export interface VideoCard {
  id: string;
  headline: string;
  what_happened: string;
  why_it_matters: string;
  signal_score: number;
  action_type: string;
  action_text: string;
  impact: string;
  prediction: {
    statement: string;
    probability: number;
    resolves_at: string;
  };
}

export interface VideoManifest {
  title: string;
  date: string;
  beat: string;
  role: string;
  audio_url: string;
  audio_duration: number;
  total_frames: number;
  fps: number;
  sections: Array<{
    type: string;
    cardIndex?: number;
    start: number;
    end: number;
  }>;
  cards: VideoCard[];
  safely_ignore: string[];
  cta: {
    text: string;
    url: string;
    elo_baseline: number;
  };
  words: WordTimestamp[];
}

export const PithVerticalVideo: React.FC<{ manifest: VideoManifest }> = ({
  manifest,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();
  const currentTime = frame / fps;

  // Active word in current frame
  const activeWordIndex = manifest.words.findIndex(
    (w) => currentTime >= w.start && currentTime <= w.end
  );

  // Determine active section
  const currentSection = manifest.sections.find(
    (s) => currentTime >= s.start && currentTime < s.end
  ) || manifest.sections[manifest.sections.length - 1];

  const activeCardIndex = currentSection?.cardIndex ?? 0;
  const activeCard = manifest.cards[activeCardIndex] || manifest.cards[0];

  // 0:00 - 0:03 Filter Sweep Transition
  const isIntro = currentTime < 3.2;
  const sweepProgress = interpolate(currentTime, [0, 3.2], [0, 1], {
    extrapolateRight: "clamp",
  });

  // Outro transition
  const isOutro = currentTime >= (manifest.sections.find(s => s.type === "safely_ignore")?.start || 85);
  const isFinalCta = currentTime >= (manifest.sections.find(s => s.type === "outro_cta")?.start || 91);

  // Card spring animation
  const cardSection = manifest.sections.find(
    (s) => s.type === "card" && s.cardIndex === activeCardIndex
  );
  const cardLocalTime = cardSection ? Math.max(0, currentTime - cardSection.start) : 0;
  const cardEntrance = spring({
    frame: Math.round(cardLocalTime * fps),
    fps,
    config: { damping: 14, stiffness: 120 },
  });

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: "#07080A",
        color: "#EDEDED",
        fontFamily: "-apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        position: "relative",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        padding: "60px 48px",
        boxSizing: "border-box",
      }}
    >
      {/* Background Audio */}
      {manifest.audio_url && (
        <Audio src={staticFile(manifest.audio_url)} />
      )}

      {/* Cybernetic Grid & Ambient Atmosphere */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(rgba(255, 255, 255, 0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(255, 255, 255, 0.03) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          top: -200,
          right: -200,
          width: 700,
          height: 700,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(255, 176, 0, 0.12) 0%, transparent 65%)",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: -150,
          left: -150,
          width: 600,
          height: 600,
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(16, 185, 129, 0.10) 0%, transparent 65%)",
          pointerEvents: "none",
        }}
      />

      {/* ---------------------------------------------------------------------- */}
      {/* STAGE 1: 0:00–0:03 Noise-to-Signal Filter Sweep Overlay                 */}
      {/* ---------------------------------------------------------------------- */}
      {isIntro && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            zIndex: 100,
            backgroundColor: "#07080A",
            opacity: 1 - sweepProgress,
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: 40,
          }}
        >
          {/* Audio Oscilloscope Sweep Bars */}
          <div style={{ display: "flex", gap: 10, height: 120, alignItems: "center", marginBottom: 40 }}>
            {Array.from({ length: 24 }).map((_, i) => {
              const h = Math.sin(frame * 0.3 + i * 0.4) * 50 + 60;
              return (
                <div
                  key={i}
                  style={{
                    width: 8,
                    height: h,
                    backgroundColor: i % 2 === 0 ? "#FFB000" : "#10B981",
                    borderRadius: 4,
                  }}
                />
              );
            })}
          </div>

          <div style={{ fontSize: 72, fontWeight: 900, letterSpacing: 12, color: "#FFB000", marginBottom: 12 }}>
            P I T H
          </div>
          <div style={{ fontSize: 24, letterSpacing: 4, color: "#A3A3A3", fontFamily: "monospace" }}>
            NOISE-TO-SIGNAL FILTER SWEEP
          </div>
          <div style={{ marginTop: 24, fontSize: 18, color: "#10B981", fontFamily: "monospace" }}>
            SHREDDING 99.4% OF MARKETING NOISE...
          </div>
        </div>
      )}

      {/* ---------------------------------------------------------------------- */}
      {/* STAGE 2: Top Persistent HUD Header                                     */}
      {/* ---------------------------------------------------------------------- */}
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255, 255, 255, 0.12)",
          paddingBottom: 24,
          marginBottom: 36,
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
          <div style={{ width: 18, height: 18, backgroundColor: "#FFB000", borderRadius: 3 }} />
          <div>
            <div style={{ fontSize: 32, fontWeight: 900, letterSpacing: 3, color: "#FFF" }}>PITH</div>
            <div style={{ fontSize: 16, color: "#888", fontFamily: "monospace", letterSpacing: 1 }}>
              DAILY TECH INTELLIGENCE
            </div>
          </div>
        </div>

        <div style={{ textAlign: "right", fontFamily: "monospace" }}>
          <div style={{ fontSize: 20, color: "#10B981", fontWeight: 700 }}>
            {manifest.role.toUpperCase()} LENS
          </div>
          <div style={{ fontSize: 16, color: "#666" }}>{manifest.date}</div>
        </div>
      </header>

      {/* ---------------------------------------------------------------------- */}
      {/* STAGE 3: Main Dynamic Content Area (Cards vs Safely Ignore vs CTA)     */}
      {/* ---------------------------------------------------------------------- */}
      <div style={{ flex: 1, display: "flex", flexDirection: "column", zIndex: 10 }}>
        {!isOutro && activeCard && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              transform: `translateY(${(1 - cardEntrance) * 40}px)`,
              opacity: cardEntrance,
            }}
          >
            {/* Story Card Frame */}
            <div
              style={{
                backgroundColor: "rgba(18, 20, 26, 0.85)",
                border: "1px solid rgba(255, 176, 0, 0.35)",
                borderRadius: 24,
                padding: "44px 36px",
                boxShadow: "0 24px 60px rgba(0, 0, 0, 0.6)",
                marginBottom: 30,
              }}
            >
              {/* Card Meta Top Line */}
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  marginBottom: 24,
                }}
              >
                <div
                  style={{
                    fontFamily: "monospace",
                    fontSize: 20,
                    fontWeight: 700,
                    color: "#FFB000",
                    letterSpacing: 2,
                  }}
                >
                  SHIFT {activeCardIndex + 1} OF 3
                </div>
                <div
                  style={{
                    backgroundColor: "rgba(16, 185, 129, 0.15)",
                    border: "1px solid #10B981",
                    color: "#10B981",
                    padding: "6px 16px",
                    borderRadius: 999,
                    fontSize: 18,
                    fontWeight: 800,
                    letterSpacing: 1,
                    textTransform: "uppercase",
                  }}
                >
                  {activeCard.action_type}
                </div>
              </div>

              {/* Card Headline */}
              <h1
                style={{
                  fontSize: 44,
                  fontWeight: 800,
                  lineHeight: 1.25,
                  color: "#FFFFFF",
                  margin: "0 0 28px 0",
                  fontFamily: "Georgia, serif",
                }}
              >
                {activeCard.headline}
              </h1>

              {/* Signal Score Bar Gauge */}
              <div style={{ marginBottom: 32 }}>
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    fontSize: 18,
                    fontFamily: "monospace",
                    marginBottom: 10,
                    color: "#D4D4D8",
                  }}
                >
                  <span>STRUCTURAL SIGNAL SCORE</span>
                  <span style={{ color: "#FFB000", fontWeight: 800 }}>
                    {activeCard.signal_score.toFixed(1)} / 100
                  </span>
                </div>
                <div
                  style={{
                    width: "100%",
                    height: 16,
                    backgroundColor: "rgba(255, 255, 255, 0.08)",
                    borderRadius: 8,
                    overflow: "hidden",
                  }}
                >
                  <div
                    style={{
                      height: "100%",
                      width: `${Math.min(100, activeCard.signal_score * cardEntrance)}%`,
                      background: "linear-gradient(90deg, #D97706, #FFB000, #FCD34D)",
                      borderRadius: 8,
                    }}
                  />
                </div>
              </div>

              {/* Role Action Directive */}
              <div
                style={{
                  backgroundColor: "rgba(255, 255, 255, 0.04)",
                  borderLeft: "6px solid #10B981",
                  padding: "20px 24px",
                  borderRadius: 12,
                  marginBottom: 28,
                }}
              >
                <div style={{ fontSize: 16, fontFamily: "monospace", color: "#10B981", fontWeight: 700, marginBottom: 6 }}>
                  ACTION DIRECTIVE
                </div>
                <div style={{ fontSize: 24, fontWeight: 600, color: "#EDEDED", lineHeight: 1.4 }}>
                  {activeCard.action_text || activeCard.why_it_matters}
                </div>
              </div>

              {/* Live Prediction Probability Gauge */}
              {activeCard.prediction && (
                <div
                  style={{
                    display: "flex",
                    alignItems: "center",
                    gap: 20,
                    backgroundColor: "rgba(0, 229, 255, 0.06)",
                    border: "1px solid rgba(0, 229, 255, 0.25)",
                    padding: "18px 24px",
                    borderRadius: 14,
                  }}
                >
                  <div
                    style={{
                      width: 64,
                      height: 64,
                      borderRadius: "50%",
                      border: "4px solid #00E5FF",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontSize: 22,
                      fontWeight: 900,
                      color: "#00E5FF",
                      fontFamily: "monospace",
                    }}
                  >
                    {Math.round(activeCard.prediction.probability * 100)}%
                  </div>
                  <div style={{ flex: 1 }}>
                    <div style={{ fontSize: 14, fontFamily: "monospace", color: "#00E5FF", fontWeight: 700 }}>
                      ON-RECORD PREDICTION &bull; RESOLVES {activeCard.prediction.resolves_at}
                    </div>
                    <div style={{ fontSize: 18, color: "#CCC", marginTop: 4 }}>
                      {activeCard.prediction.statement}
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------------- */}
        {/* STAGE 4: Safely Ignore Flash (0:50 - 0:55)                             */}
        {/* ---------------------------------------------------------------------- */}
        {isOutro && !isFinalCta && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              padding: "0 20px",
            }}
          >
            <div style={{ fontSize: 20, color: "#EF4444", fontFamily: "monospace", fontWeight: 800, letterSpacing: 2 }}>
              THE NOISE SHREDDER
            </div>
            <h2 style={{ fontSize: 48, fontWeight: 900, color: "#FFF", margin: "12px 0 32px 0" }}>
              Safely Ignore Today
            </h2>
            <div style={{ display: "flex", flexDirection: "column", gap: 18 }}>
              {manifest.safely_ignore.map((noise, idx) => (
                <div
                  key={idx}
                  style={{
                    backgroundColor: "rgba(239, 68, 68, 0.08)",
                    border: "1px solid rgba(239, 68, 68, 0.3)",
                    padding: "20px 24px",
                    borderRadius: 14,
                    display: "flex",
                    alignItems: "center",
                    gap: 16,
                  }}
                >
                  <span style={{ fontSize: 28, color: "#EF4444" }}>✕</span>
                  <span style={{ fontSize: 24, color: "#A3A3A3", textDecoration: "line-through" }}>
                    {noise}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* ---------------------------------------------------------------------- */}
        {/* STAGE 5: Outro CTA (0:55 - 1:00)                                       */}
        {/* ---------------------------------------------------------------------- */}
        {isFinalCta && (
          <div
            style={{
              flex: 1,
              display: "flex",
              flexDirection: "column",
              justifyContent: "center",
              alignItems: "center",
              textAlign: "center",
              padding: "0 20px",
            }}
          >
            <div
              style={{
                width: 96,
                height: 96,
                borderRadius: "50%",
                backgroundColor: "rgba(255, 176, 0, 0.15)",
                border: "2px solid #FFB000",
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontSize: 48,
                color: "#FFB000",
                marginBottom: 28,
              }}
            >
              ◈
            </div>
            <div style={{ fontSize: 24, color: "#10B981", fontFamily: "monospace", fontWeight: 700, letterSpacing: 2 }}>
              MATHEMATICAL CALIBRATION LEDGER
            </div>
            <h2 style={{ fontSize: 56, fontWeight: 900, color: "#FFF", margin: "16px 0 24px 0", lineHeight: 1.15 }}>
              Beat our odds at pith.sh
            </h2>
            <p style={{ fontSize: 26, color: "#A3A3A3", maxWidth: 700, lineHeight: 1.5, marginBottom: 40 }}>
              Vote against our forecasts on the live immutable ledger. Earn reader ELO when you disprove consensus.
            </p>

            <div
              style={{
                backgroundColor: "#FFB000",
                color: "#07080A",
                padding: "22px 48px",
                borderRadius: 16,
                fontSize: 28,
                fontWeight: 900,
                letterSpacing: 1,
              }}
            >
              VISIT PITH.SH
            </div>
          </div>
        )}
      </div>

      {/* ---------------------------------------------------------------------- */}
      {/* STAGE 6: Bottom Word-by-Word Subtitle Bar Synced to Audio              */}
      {/* ---------------------------------------------------------------------- */}
      <footer
        style={{
          borderTop: "1px solid rgba(255, 255, 255, 0.1)",
          paddingTop: 24,
          minHeight: 120,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          zIndex: 10,
        }}
      >
        <div
          style={{
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "6px 12px",
            maxWidth: 960,
          }}
        >
          {manifest.words
            .slice(Math.max(0, activeWordIndex - 4), activeWordIndex + 7)
            .map((w, idx) => {
              const isCurrent = currentTime >= w.start && currentTime <= w.end;
              return (
                <span
                  key={idx}
                  style={{
                    fontSize: isCurrent ? 34 : 28,
                    fontWeight: isCurrent ? 900 : 500,
                    color: isCurrent ? "#FFB000" : "rgba(255, 255, 255, 0.55)",
                    backgroundColor: isCurrent ? "rgba(255, 176, 0, 0.18)" : "transparent",
                    padding: "2px 8px",
                    borderRadius: 6,
                    transform: isCurrent ? "scale(1.08)" : "none",
                    transition: "all 0.08s ease",
                  }}
                >
                  {w.word}
                </span>
              );
            })}
        </div>
      </footer>
    </div>
  );
};
