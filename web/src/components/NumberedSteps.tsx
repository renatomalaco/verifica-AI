export function NumberedSteps({ steps }: { steps: string[] }) {
  return (
    <ol className="numbered-steps">
      {steps.map((step, i) => (
        <li key={i}>
          <span className="todo__num" aria-hidden="true">
            {i + 1}
          </span>
          <span>{step}</span>
        </li>
      ))}
    </ol>
  )
}
