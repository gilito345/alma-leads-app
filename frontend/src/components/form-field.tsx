/** A labeled text input with an optional hint and an error that replaces it. */
export function FormField(props: {
  id: string;
  name: string;
  label: string;
  type?: string;
  autoComplete?: string;
  defaultValue?: string;
  hint?: string;
  error?: string;
}) {
  const describedBy = props.error ? `${props.id}-error` : props.hint ? `${props.id}-hint` : undefined;
  return (
    <div>
      <label htmlFor={props.id} className="block text-sm font-medium">
        {props.label}
      </label>
      <input
        id={props.id}
        name={props.name}
        type={props.type ?? "text"}
        autoComplete={props.autoComplete}
        defaultValue={props.defaultValue}
        required
        aria-invalid={Boolean(props.error)}
        aria-describedby={describedBy}
        className="mt-1.5 block w-full rounded-lg border border-line bg-white px-3.5 py-2.5 outline-none focus:border-accent focus:ring-2 focus:ring-accent/20 aria-invalid:border-danger"
      />
      {props.error ? (
        <p id={`${props.id}-error`} className="mt-1.5 text-sm text-danger">
          {props.error}
        </p>
      ) : (
        props.hint && (
          <p id={`${props.id}-hint`} className="mt-1.5 text-xs text-muted">
            {props.hint}
          </p>
        )
      )}
    </div>
  );
}
