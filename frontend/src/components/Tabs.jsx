export default function Tabs({ items, value, onChange, className = '' }) {
  return (
    <div role="tablist" className={`flex max-w-full gap-5 overflow-x-auto border-b border-slate-200 ${className}`}>
      {items.map(item => (
        <button
          key={item.key}
          type="button"
          role="tab"
          aria-selected={value === item.key}
          onClick={() => onChange(item.key)}
          className={`-mb-px shrink-0 border-b-2 px-1 py-3 text-sm font-semibold transition-colors focus-visible:ring-primary ${value === item.key ? 'border-primary text-primary' : 'border-transparent text-gray-500 hover:border-slate-300 hover:text-gray-800'}`}
        >
          {item.label}
        </button>
      ))}
    </div>
  )
}
