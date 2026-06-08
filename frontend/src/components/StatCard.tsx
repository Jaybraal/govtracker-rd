import clsx from 'clsx'
import { Link } from 'react-router-dom'

interface Props {
  label: string
  value: string | number
  sub?: string
  icon?: React.ReactNode
  color?: 'blue' | 'green' | 'yellow' | 'red' | 'purple'
  to?: string
}

const colorMap = {
  blue:   'text-blue-400 bg-blue-900/20',
  green:  'text-green-400 bg-green-900/20',
  yellow: 'text-yellow-400 bg-yellow-900/20',
  red:    'text-red-400 bg-red-900/20',
  purple: 'text-purple-400 bg-purple-900/20',
}

export default function StatCard({ label, value, sub, icon, color = 'blue', to }: Props) {
  const content = (
    <>
      <div className="flex items-start justify-between">
        <p className="text-xs text-gray-500 uppercase tracking-wider">{label}</p>
        {icon && (
          <span className={clsx('p-2 rounded-lg text-lg', colorMap[color])}>
            {icon}
          </span>
        )}
      </div>
      <p className="text-2xl font-bold text-white mt-1">{value}</p>
      {sub && <p className="text-xs text-gray-500">{sub}</p>}
    </>
  )

  if (to) {
    return (
      <Link
        to={to}
        className="stat-card block transition-colors hover:border-gov-600/50 hover:bg-gray-800/60 cursor-pointer"
      >
        {content}
      </Link>
    )
  }

  return (
    <div className="stat-card">
      {content}
    </div>
  )
}
