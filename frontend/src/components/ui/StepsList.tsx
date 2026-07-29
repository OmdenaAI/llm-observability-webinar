interface StepsListProps {
  /** Ordered list of step descriptions. Can include JSX (e.g. <code>). */
  steps: React.ReactNode[];
}

/**
 * Numbered execution steps shown at the top of each moment view, so the
 * presenter can follow along and verify the scenario runs the way it
 * should before the actual demo.
 *
 * @param props - Component props.
 */
export function StepsList({ steps }: StepsListProps) {
  return (
    <ol className="steps-list">
      {steps.map((step, index) => (
        // eslint-disable-next-line react/no-array-index-key
        <li key={index}>{step}</li>
      ))}
    </ol>
  );
}
