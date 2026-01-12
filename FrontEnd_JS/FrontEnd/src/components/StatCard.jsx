export function StatsCard({ stat }) {
  const Icon = stat.icon;
  const colorClasses = {
    blue: 'bg-blue-100 text-blue-600',
    green: 'bg-green-100 text-green-600',
    purple: 'bg-purple-100 text-purple-600',
    orange: 'bg-orange-100 text-orange-600'
  };

  return (
    <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
      <div className="flex items-center justify-between mb-4">
        <div className={`w-12 h-12 rounded-lg flex items-center justify-center ${colorClasses[stat.color]}`}>
          <Icon className="w-6 h-6" />
        </div>
        <span className={`text-sm font-medium ${stat.change.startsWith('+') ? 'text-green-600' : 'text-red-600'}`}>
          {stat.change}
        </span>
      </div>
      <h3 className="text-2xl font-bold text-gray-900 mb-1">{stat.value}</h3>
      <p className="text-sm text-gray-600">{stat.label}</p>
    </div>
  );
}