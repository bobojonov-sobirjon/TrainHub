export function PlaceholderPage({ title }: { title: string }) {
  return (
    <div>
      <h1>{title}</h1>
      <p className="muted">Этот раздел будет подключён позже.</p>
    </div>
  );
}
