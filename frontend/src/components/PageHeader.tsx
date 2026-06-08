interface Props {
  title: string
  subtitle?: string
  actions?: React.ReactNode
}

export default function PageHeader({ title, subtitle, actions }: Props) {
  return (
    <div className="flex items-start justify-between px-6 pt-6 pb-4 border-b border-gray-800">
      <div>
        <h1 className="text-xl font-bold text-white">{title}</h1>
        {subtitle && <p className="text-sm text-gray-400 mt-0.5">{subtitle}</p>}
      </div>
      {actions && <div className="flex items-center gap-2">{actions}</div>}
    </div>
  )
}
