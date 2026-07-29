type BadgeVariant = "success" | "error" | "warning" | "neutral";

interface BadgeProps {
  /** Visual/semantic variant — determines color. */
  variant: BadgeVariant;
  /** Label text shown inside the badge. */
  children: React.ReactNode;
}

/**
 * Small status pill used throughout the moment views to show pass/fail,
 * success/error, or other binary-ish states (e.g. "Quality trap
 * detected", "Failed over", "All calls succeeded").
 *
 * @param props - Component props.
 */
export function Badge({ variant, children }: BadgeProps) {
  return (
    <span className={`badge badge-${variant}`}>
      <span className="badge-dot" />
      {children}
    </span>
  );
}
