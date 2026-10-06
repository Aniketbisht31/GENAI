import { useMemo, useState } from 'react'
import { ChevronLeft, ChevronRight, Inbox, Search } from 'lucide-react'

export default function DataTable({ title, columns, rows, rowKey = 'id', emptyMessage = 'No records to show', emptyAction, pageSize = 8, className = '' }) {
  const [query, setQuery] = useState('')
  const [page, setPage] = useState(1)
  const filteredRows = useMemo(() => {
    const normalized = query.trim().toLowerCase()
    if (!normalized) return rows
    return rows.filter(row => columns.some(column => {
      const value = column.searchValue ? column.searchValue(row) : row[column.accessor]
      return String(value ?? '').toLowerCase().includes(normalized)
    }))
  }, [rows, columns, query])
  const pages = Math.max(1, Math.ceil(filteredRows.length / pageSize))
  const visibleRows = filteredRows.slice((page - 1) * pageSize, page * pageSize)

  return (
    <section className={`overflow-hidden rounded-md border border-slate-200 bg-white shadow-sm ${className}`}>
      <div className="flex min-h-12 flex-wrap items-center justify-between gap-3 bg-table-purple px-4 py-3 text-white">
        <h2 className="text-sm font-bold sm:text-base">{title}</h2>
        <label className="relative w-full sm:w-64">
          <span className="sr-only">Search {title}</span>
          <Search size={16} aria-hidden="true" className="absolute left-3 top-1/2 -translate-y-1/2 text-slate-500" />
          <input value={query} onChange={e => { setQuery(e.target.value); setPage(1) }} className="w-full rounded-md border border-white/40 bg-white py-2 pl-9 pr-3 text-xs text-gray-800 placeholder:text-gray-500 focus-visible:ring-white" placeholder="Search records" />
        </label>
      </div>
      <div className="max-w-full overflow-x-auto">
        <table className="w-full min-w-[640px] border-collapse text-left text-sm">
          <thead className="bg-table-lavender text-gray-800">
            <tr>{columns.map(column => <th key={column.key || column.label} scope="col" className="whitespace-nowrap px-4 py-3 text-xs font-bold uppercase tracking-wide">{column.label}</th>)}</tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {visibleRows.map((row, index) => (
              <tr key={row[rowKey] ?? index} className="hover:bg-blue-50/60">
                {columns.map(column => <td key={column.key || column.label} className="px-4 py-3 align-middle text-gray-700">{column.render ? column.render(row) : row[column.accessor]}</td>)}
              </tr>
            ))}
            {visibleRows.length === 0 && <tr><td colSpan={columns.length} className="px-4 py-12 text-center">
              <div className="flex flex-col items-center gap-2 text-gray-500"><Inbox size={28} className="text-slate-400" /><p className="font-semibold">{query ? 'No matching records' : emptyMessage}</p>{emptyAction}</div>
            </td></tr>}
          </tbody>
        </table>
      </div>
      <div className="flex items-center justify-end gap-3 border-t border-slate-100 px-4 py-3 text-xs text-gray-600">
        <span>{filteredRows.length ? `${(page - 1) * pageSize + 1}–${Math.min(page * pageSize, filteredRows.length)} of ${filteredRows.length}` : '0 records'}</span>
        <button type="button" aria-label="Previous page" disabled={page <= 1} onClick={() => setPage(p => p - 1)} className="rounded border border-slate-300 p-1.5 hover:bg-slate-50 disabled:opacity-40"><ChevronLeft size={16} /></button>
        <button type="button" aria-label="Next page" disabled={page >= pages} onClick={() => setPage(p => p + 1)} className="rounded border border-slate-300 p-1.5 hover:bg-slate-50 disabled:opacity-40"><ChevronRight size={16} /></button>
      </div>
    </section>
  )
}
