import type { SelectOption } from "./Select";

export function ChipGroup({
  options,
  values,
  onChange,
  empty = "Нет вариантов",
}: {
  options: SelectOption[];
  values: string[];
  onChange: (values: string[]) => void;
  empty?: string;
}) {
  if (!options.length) {
    return <p className="muted">{empty}</p>;
  }

  return (
    <div className="chip-group">
      {options.map((option) => {
        const active = values.includes(option.value);
        return (
          <button
            type="button"
            key={option.value}
            className={`chip${active ? " is-active" : ""}`}
            onClick={() =>
              onChange(active ? values.filter((item) => item !== option.value) : [...values, option.value])
            }
          >
            {option.label}
          </button>
        );
      })}
    </div>
  );
}
