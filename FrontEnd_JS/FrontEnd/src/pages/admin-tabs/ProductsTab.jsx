import React, { useState } from 'react';
import { Upload, Download, Plus, Search, Filter, Eye, Edit2, Trash2, X, FolderTree, ChevronDown, ChevronRight } from 'lucide-react';

const categoryTree = {
  id: 'root',
  name: 'Tất cả sản phẩm',
  children: [
    {
      id: 'electronics',
      name: 'Điện tử',
      count: 150,
      children: [
        { id: 'phones', name: 'Điện thoại', count: 45 },
        { id: 'laptops', name: 'Laptop', count: 32 },
        { id: 'tablets', name: 'Tablet', count: 18 },
        { id: 'accessories', name: 'Phụ kiện', count: 55 }
      ]
    },
    {
      id: 'fashion',
      name: 'Thời trang',
      count: 200,
      children: [
        { id: 'mens', name: 'Nam', count: 80 },
        { id: 'womens', name: 'Nữ', count: 90 },
        { id: 'kids', name: 'Trẻ em', count: 30 }
      ]
    },
    {
      id: 'home',
      name: 'Gia dụng',
      count: 120,
      children: [
        { id: 'kitchen', name: 'Nhà bếp', count: 40 },
        { id: 'furniture', name: 'Nội thất', count: 50 },
        { id: 'decor', name: 'Trang trí', count: 30 }
      ]
    }
  ]
};

const recentProducts = [
  { id: 1, name: 'iPhone 15 Pro Max', category: 'Điện thoại', price: 29990000, commission: 5, clicks: 234, conversions: 12, status: 'active' },
  { id: 2, name: 'MacBook Pro M3', category: 'Laptop', price: 45990000, commission: 4, clicks: 189, conversions: 8, status: 'active' },
  { id: 3, name: 'AirPods Pro 2', category: 'Phụ kiện', price: 6990000, commission: 6, clicks: 567, conversions: 45, status: 'active' },
  { id: 4, name: 'Samsung Galaxy S24', category: 'Điện thoại', price: 22990000, commission: 5, clicks: 198, conversions: 9, status: 'paused' }
];

function CategoryTreeNode({ node, level = 0, onSelect }) {
  const [expanded, setExpanded] = useState(level === 0);
 
  return (
    <div>
      <div
        className={`flex items-center gap-2 px-3 py-2 hover:bg-gray-50 rounded-lg cursor-pointer ${
          level > 0 ? 'ml-6' : ''
        }`}
        onClick={() => {
          if (node.children) setExpanded(!expanded);
          onSelect(node);
        }}
      >
        {node.children && (
          expanded ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />
        )}
        {!node.children && <div className="w-4" />}
        <FolderTree className="w-4 h-4 text-blue-600" />
        <span className="flex-1 text-sm font-medium">{node.name}</span>
        {node.count !== undefined && (
          <span className="text-xs bg-gray-100 px-2 py-1 rounded">{node.count}</span>
        )}
      </div>
     
      {expanded && node.children && (
        <div className="mt-1">
          {node.children.map(child => (
            <CategoryTreeNode key={child.id} node={child} level={level + 1} onSelect={onSelect} />
          ))}
        </div>
      )}
    </div>
  );
}

export default function ProductsTab() {
  const [showUpload, setShowUpload] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">Quản lý Sản phẩm</h2>
          <p className="text-gray-600 mt-1">Quản lý và cập nhật sản phẩm affiliate</p>
        </div>
        <div className="flex gap-3">
          <button
            onClick={() => setShowUpload(true)}
            className="flex items-center gap-2 px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700"
          >
            <Upload className="w-5 h-5" />
            Import File
          </button>
          <button className="flex items-center gap-2 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
            <Plus className="w-5 h-5" />
            Thêm sản phẩm
          </button>
        </div>
      </div>

      <div className="grid grid-cols-4 gap-6">
        <div className="bg-white rounded-xl p-4 shadow-sm border border-gray-200">
          <h3 className="font-semibold mb-4 flex items-center gap-2">
            <FolderTree className="w-5 h-5" />
            Danh mục sản phẩm
          </h3>
          <CategoryTreeNode node={categoryTree} onSelect={() => {}} />
        </div>

        <div className="col-span-3 bg-white rounded-xl p-6 shadow-sm border border-gray-200">
          <div className="flex gap-4 mb-6">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
              <input
                type="text"
                placeholder="Tìm kiếm sản phẩm..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full pl-10 pr-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
              />
            </div>
            <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
              <Filter className="w-5 h-5" />
              Lọc
            </button>
            <button className="flex items-center gap-2 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
              <Download className="w-5 h-5" />
              Export
            </button>
          </div>

          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-gray-200">
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Sản phẩm</th>
                  <th className="text-left py-3 px-4 text-sm font-semibold text-gray-900">Danh mục</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Giá</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Hoa hồng</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Clicks</th>
                  <th className="text-right py-3 px-4 text-sm font-semibold text-gray-900">Chuyển đổi</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-900">Trạng thái</th>
                  <th className="text-center py-3 px-4 text-sm font-semibold text-gray-900">Hành động</th>
                </tr>
              </thead>
              <tbody>
                {recentProducts.map((product) => (
                  <tr key={product.id} className="border-b border-gray-100 hover:bg-gray-50">
                    <td className="py-3 px-4">
                      <div className="font-medium text-gray-900">{product.name}</div>
                    </td>
                    <td className="py-3 px-4 text-sm text-gray-600">{product.category}</td>
                    <td className="py-3 px-4 text-right font-medium text-gray-900">
                      {product.price.toLocaleString('vi-VN')}đ
                    </td>
                    <td className="py-3 px-4 text-right text-sm text-gray-600">{product.commission}%</td>
                    <td className="py-3 px-4 text-right text-sm text-gray-600">{product.clicks}</td>
                    <td className="py-3 px-4 text-right font-medium text-green-600">{product.conversions}</td>
                    <td className="py-3 px-4 text-center">
                      <span className={`inline-block px-2 py-1 text-xs font-medium rounded ${
                        product.status === 'active' ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-700'
                      }`}>
                        {product.status === 'active' ? 'Hoạt động' : 'Tạm dừng'}
                      </span>
                    </td>
                    <td className="py-3 px-4">
                      <div className="flex items-center justify-center gap-2">
                        <button className="p-1 hover:bg-gray-100 rounded">
                          <Eye className="w-4 h-4 text-gray-600" />
                        </button>
                        <button className="p-1 hover:bg-gray-100 rounded">
                          <Edit2 className="w-4 h-4 text-blue-600" />
                        </button>
                        <button className="p-1 hover:bg-gray-100 rounded">
                          <Trash2 className="w-4 h-4 text-red-600" />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {showUpload && (
        <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
          <div className="bg-white rounded-xl p-6 w-full max-w-lg">
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-xl font-bold">Import Sản phẩm từ File</h3>
              <button onClick={() => setShowUpload(false)} className="p-1 hover:bg-gray-100 rounded">
                <X className="w-5 h-5" />
              </button>
            </div>
           
            <div className="border-2 border-dashed border-gray-300 rounded-lg p-8 text-center mb-4">
              <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
              <p className="text-gray-600 mb-2">Kéo thả file hoặc click để chọn</p>
              <p className="text-sm text-gray-400">Hỗ trợ: Excel (.xlsx), CSV (.csv)</p>
              <input type="file" className="hidden" accept=".xlsx,.csv" />
              <button className="mt-4 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Chọn file
              </button>
            </div>

            <div className="bg-blue-50 border border-blue-200 rounded-lg p-4 mb-4">
              <h4 className="font-semibold text-blue-900 mb-2">📋 Format file yêu cầu:</h4>
              <ul className="text-sm text-blue-800 space-y-1">
                <li>• Cột 1: Tên sản phẩm</li>
                <li>• Cột 2: Danh mục (ID hoặc tên)</li>
                <li>• Cột 3: Giá</li>
                <li>• Cột 4: Hoa hồng (%)</li>
                <li>• Cột 5: Link affiliate</li>
                <li>• Cột 6: Mô tả</li>
              </ul>
            </div>

            <div className="flex gap-3">
              <button className="flex-1 px-4 py-2 border border-gray-300 rounded-lg hover:bg-gray-50">
                Tải file mẫu
              </button>
              <button className="flex-1 px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700">
                Upload & Import
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
