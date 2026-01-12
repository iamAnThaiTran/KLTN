export function StatisticsTab() {
  const [dateRange, setDateRange] = useState('7days');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Thống kê & Báo cáo</h2>
          <p className="text-gray-600 mt-1">Phân tích hiệu suất affiliate</p>
        </div>
        <div className="flex gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="7days">7 ngày qua</option>
            <option value="30days">30 ngày qua</option>
            <option value="90days">90 ngày qua</option>
            <option value="custom">Tùy chỉnh</option>
          </select>
          <button className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700">
            <Download className="w-5 h-5" />
            Export Excel
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <FileText className="w-5 h-5" />
            Export PDF
          </button>
        </div>
      </div>

      <div className="grid grid-cols-2 gap-6">
        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <h3 className="text-lg font-bold mb-4">Doanh thu theo Danh mục</h3>
          <div className="h-80 flex items-center justify-center bg-gray-50 rounded-lg">
            <PieChart className="w-20 h-20 text-gray-300" />
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <h3 className="text-lg font-bold mb-4">Tỷ lệ Chuyển đổi</h3>
          <div className="h-80 flex items-center justify-center bg-gray-50 rounded-lg">
            <BarChart3 className="w-20 h-20 text-gray-300" />
          </div>
        </div>

        <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200 col-span-2">
          <h3 className="text-lg font-bold mb-4">Clicks & Doanh thu theo Thời gian</h3>
          <div className="h-80 flex items-center justify-center bg-gray-50 rounded-lg">
            <Activity className="w-20 h-20 text-gray-300" />
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl p-6 shadow-sm border border-gray-200">
        <h3 className="text-lg font-bold mb-4">Top 10 Sản phẩm có hiệu suất cao nhất</h3>
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="border-b border-gray-200">
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Xếp hạng</th>
                <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Sản phẩm</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Clicks</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Chuyển đổi</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Tỷ lệ</th>
                <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Doanh thu</th>
              </tr>
            </thead>
            <tbody>
              {[1,2,3,4,5].map((rank) => (
                <tr key={rank} className="border-b border-gray-100 hover:bg-gray-50">
                  <td className="py-3 px-4">
                    <div className="w-8 h-8 bg-blue-100 text-blue-600 rounded-full flex items-center justify-center font-bold">
                      {rank}
                    </div>
                  </td>
                  <td className="py-3 px-4 font-medium text-gray-900">iPhone 15 Pro Max</td>
                  <td className="py-3 px-4 text-right text-gray-600">1,234</td>
                  <td className="py-3 px-4 text-right text-gray-600">98</td>
                  <td className="py-3 px-4 text-right font-medium text-green-600">7.9%</td>
                  <td className="py-3 px-4 text-right font-bold text-gray-900">147.2M</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}