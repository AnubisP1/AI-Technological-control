import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Database, Table2 } from 'lucide-react'
import { Container } from '@/components/marketing/Section'
import { cn } from '@/lib/utils'
import { fetchNsiTables, fetchNsiTableContent, type NsiDatabaseName } from '@/lib/api'

/**
 * "База НСИ" (Фаза 17, часть 5) — просмотрщик содержимого справочника
 * нормативно-справочной информации целиком, по идее из UI UX reference/
 * ai_technologist_site/nsi.html. В отличие от экрана "Экспертиза НСИ"
 * (сверка КОНКРЕТНОЙ загруженной детали со справочником), здесь — сырое
 * содержимое всех таблиц обеих независимых баз (металл/аддитив), без
 * привязки к детали: реальные строки из metal.sqlite/additive.sqlite
 * через новые эндпоинты /nsi/{database}/tables[/​{table}], не выдуманная
 * витрина.
 */

const DATABASE_LABELS: Record<NsiDatabaseName, string> = {
  metal: 'Металлообработка',
  additive: 'Аддитивные технологии',
}

export function NsiBrowserPage() {
  const [database, setDatabase] = useState<NsiDatabaseName>('metal')
  const [selectedTable, setSelectedTable] = useState<string | null>(null)

  const tablesQuery = useQuery({
    queryKey: ['nsi-tables', database],
    queryFn: () => fetchNsiTables(database),
  })

  const contentQuery = useQuery({
    queryKey: ['nsi-table-content', database, selectedTable],
    queryFn: () => fetchNsiTableContent(database, selectedTable!),
    enabled: selectedTable !== null,
  })

  function handleDatabaseChange(next: NsiDatabaseName) {
    setDatabase(next)
    setSelectedTable(null)
  }

  return (
    <Container className="max-w-6xl py-10">
      <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold tracking-tight text-ink">База НСИ</h1>
          <p className="mt-1 max-w-2xl text-sm text-ink-dim">
            Содержимое локальной нормативно-справочной базы (SQLite) целиком — материалы,
            оборудование, оснастка, операции, матрицы совместимости, без привязки к конкретной
            загруженной детали.
          </p>
        </div>
        <div className="flex rounded-lg border border-border bg-surface p-1 text-sm">
          {(Object.keys(DATABASE_LABELS) as NsiDatabaseName[]).map((db) => (
            <button
              key={db}
              onClick={() => handleDatabaseChange(db)}
              className={cn(
                'rounded-md px-3 py-1.5 transition-colors',
                database === db ? 'bg-brand text-white' : 'text-ink-dim hover:text-ink'
              )}
            >
              {DATABASE_LABELS[db]}
            </button>
          ))}
        </div>
      </div>

      <div className="grid grid-cols-1 gap-4 lg:grid-cols-[260px_1fr]">
        <div className="rounded-2xl border border-border bg-surface p-2">
          <div className="mb-1 flex items-center gap-2 px-2 py-1.5 text-xs font-medium uppercase tracking-wider text-ink-dim">
            <Database className="h-3.5 w-3.5" />
            Таблицы
            {tablesQuery.data && (
              <span className="ml-auto font-mono text-[10px] text-ink-dim">{tablesQuery.data.length}</span>
            )}
          </div>
          {tablesQuery.isLoading && <div className="px-2 py-2 text-xs text-ink-dim">Загрузка…</div>}
          {tablesQuery.isError && (
            <div className="px-2 py-2 text-xs text-red-600">{(tablesQuery.error as Error).message}</div>
          )}
          <div className="max-h-[70vh] overflow-y-auto">
            {tablesQuery.data?.map((table) => (
              <button
                key={table.name}
                onClick={() => setSelectedTable(table.name)}
                className={cn(
                  'flex w-full items-center justify-between gap-2 rounded-lg px-2 py-1.5 text-left text-xs transition-colors',
                  selectedTable === table.name ? 'bg-brand/10 text-brand' : 'text-ink hover:bg-muted'
                )}
              >
                <span className="truncate font-mono">{table.name}</span>
                <span className="shrink-0 font-mono text-[10px] text-ink-dim">{table.row_count}</span>
              </button>
            ))}
          </div>
        </div>

        <div className="min-w-0 rounded-2xl border border-border bg-surface p-5">
          {!selectedTable && (
            <div className="flex min-h-[300px] items-center justify-center text-sm text-ink-dim">
              Выберите таблицу слева, чтобы увидеть содержимое
            </div>
          )}

          {selectedTable && contentQuery.isLoading && (
            <div className="flex min-h-[300px] items-center justify-center text-sm text-ink-dim">
              Загрузка…
            </div>
          )}

          {selectedTable && contentQuery.data && (
            <div>
              <div className="mb-3 flex items-center justify-between gap-3">
                <div className="flex items-center gap-2">
                  <Table2 className="h-4 w-4 text-brand" />
                  <h2 className="font-mono text-sm font-semibold text-ink">{contentQuery.data.name}</h2>
                </div>
                <span className="font-mono text-xs text-ink-dim">
                  {contentQuery.data.total_row_count} строк
                  {contentQuery.data.truncated && ' (показаны первые 200)'}
                </span>
              </div>
              <div className="overflow-x-auto rounded-xl border border-border">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="bg-muted/60 text-left text-ink-dim">
                      {contentQuery.data.columns.map((col) => (
                        <th key={col} className="whitespace-nowrap px-2.5 py-1.5 font-mono font-medium">
                          {col}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {contentQuery.data.rows.map((row, i) => (
                      <tr key={i} className="border-t border-border">
                        {row.map((value, j) => (
                          <td key={j} className="whitespace-nowrap px-2.5 py-1.5 font-mono text-ink">
                            {value || '—'}
                          </td>
                        ))}
                      </tr>
                    ))}
                    {contentQuery.data.rows.length === 0 && (
                      <tr>
                        <td colSpan={contentQuery.data.columns.length} className="px-2.5 py-6 text-center text-ink-dim">
                          Таблица пуста
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      </div>
    </Container>
  )
}
