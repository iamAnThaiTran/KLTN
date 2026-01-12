import React from 'react';
import { Package, Activity, TrendingUp, DollarSign, BarChart3, PieChart } from 'lucide-react';

const statsData = [
  { label: 'Tổng sản phẩm', value: '470', change: '+12%', icon: Package, color: 'blue' },
  { label: 'Lượt click', value: '12,543', change: '+23%', icon: Activity, color: 'green' },
  { label: 'Chuyển đổi', value: '8.5%', change: '+2.1%', icon: TrendingUp, color: 'purple' },
  { label: 'Doanh thu', value: '45.2M', change: '+18%', icon: DollarSign, color: 'orange' }
];

function StatsCard({ stat }) {
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

export default function DashboardTab() {
  return (
    <div className="space-y-6">
      <div className="grid grid-cols-4 gap-6">
        {statsData.map((stat, idx) => (
          <StatsCard key={idx} stat={stat} />
        ))}
      </div>
     
      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <h3 className="text-lg font-bold mb-4">Xu hướng Click & Chuyển đổi</h3>
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
            <BarChart3 className="w-16 h-16 text-gray-300" />
            <p className="ml-4 text-gray-400">Biểu đồ thống kê</p>
          </div>
        </div>
       
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <h3 className="text-lg font-bold mb-4">Sản phẩm Top Performance</h3>
          <div className="h-64 flex items-center justify-center bg-gray-50 rounded-lg">
            <PieChart className="w-16 h-16 text-gray-300" />
            <p className="ml-4 text-gray-400">Biểu đồ phân bổ</p>
          </div>
        </div>
      </div>
    </div>
  );
}
