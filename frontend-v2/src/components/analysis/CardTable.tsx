export function CardTable({ columns, rows }: { columns: string[]; rows: string[][] }) {
  return (
    <div className="overflow-x-auto rounded-xl border border-border">
      <table className="w-full text-sm">
        <thead>
          <tr className="bg-muted/60">
            {columns.map((c) => (
              <th key={c} className="whitespace-nowrap px-3 py-2 text-left font-medium text-ink-dim">
                {c}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, i) => (
            <tr key={i} className="border-t border-border">
              {row.map((value, j) => (
                <td key={j} className="whitespace-nowrap px-3 py-2 font-mono text-ink">
                  {value || '—'}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
