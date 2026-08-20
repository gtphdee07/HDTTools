// Persistent (not dismissible) caution shown alongside any breakdown row
// derived from pin-weight-percentage math rather than a real scale
// reading - most commonly the pre-purchase "no rig yet" case. Deliberately
// separate from DisclaimerModal (a one-time, acknowledge-and-forget modal):
// this legal context needs to travel with the estimate every time it's
// shown, not just once per session.
export function PredictiveEstimateNotice() {
  return (
    <div
      style={{
        background: 'color-mix(in oklch, var(--state-warning) 12%, white)',
        border: '1px solid color-mix(in oklch, var(--state-warning) 40%, white)',
        borderRadius: 'var(--radius-md)',
        padding: '16px 20px',
        marginBottom: 20,
      }}
    >
      <div style={{ fontFamily: 'var(--font-display)', fontWeight: 700, fontSize: 14, marginBottom: 8 }}>
        ⚠️ Estimated Figures — Confirm Before You Buy
      </div>
      <ul style={{ margin: 0, paddingLeft: 20, fontSize: 13, color: 'var(--fg-2)', lineHeight: 'var(--leading-normal)' }}>
        <li>
          Trim, engine, axle ratio, cab/bed size, and factory options change a specific vehicle's real payload — a
          GVWR/GAWR from a compliance label is a rating, not a guarantee for every configuration.
        </li>
        <li>
          This estimate doesn't account for passengers, cargo in the cab or bed, or aftermarket accessories — all
          of which reduce what's actually left for towing.
        </li>
        <li>
          Before buying, confirm the actual ratings on that specific vehicle's own certification label, and the
          trailer's own data plate — not an average, a brochure figure, or this estimate.
        </li>
        <li>
          Actual results may differ. You are solely responsible for safe towing and for complying with all
          applicable federal and state regulations, including FMCSA and DOT requirements.
        </li>
      </ul>
    </div>
  );
}
