import React from 'react';
import CategoryProductList from './CategoryProductList';

/**
 * Demo Component - Shows how CategoryProductList works
 * 
 * This is a static demo with hardcoded data to visualize the component
 * without needing a real backend API
 */
export default function CategoryProductListDemo() {
  const handleViewMore = (categoryId, categoryName) => {
    alert(`View more for: ${categoryName}`);
  };

  return (
    <div className="min-h-screen bg-gray-50 py-8">
      <div className="max-w-7xl mx-auto">
        {/* Demo Title */}
        <div className="mb-12 text-center">
          <h1 className="text-4xl font-bold text-gray-900 mb-4">
            CategoryProductList Component Demo
          </h1>
          <p className="text-lg text-gray-600">
            Responsive product listing component with 3 parts: category header, subcategories, and products
          </p>
        </div>

        {/* Example 1: Electronics Category */}
        <div className="mb-16 bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Example 1: Electronics</h2>
          <CategoryProductList
            categoryId={1}
            categoryName="Điện tử & Công nghệ"
            onViewMore={handleViewMore}
          />
        </div>

        {/* Example 2: Fashion Category */}
        <div className="mb-16 bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Example 2: Fashion</h2>
          <CategoryProductList
            categoryId={14}
            categoryName="Thời trang & Phụ kiện"
            onViewMore={handleViewMore}
          />
        </div>

        {/* Example 3: Home & Living Category */}
        <div className="mb-16 bg-white rounded-lg shadow-sm p-6">
          <h2 className="text-2xl font-bold text-gray-900 mb-6">Example 3: Home & Living</h2>
          <CategoryProductList
            categoryId={25}
            categoryName="Gia dụng & Nội thất"
            onViewMore={handleViewMore}
          />
        </div>

        {/* Features Section */}
        <div className="bg-indigo-50 border-2 border-indigo-200 rounded-lg p-8 mt-12">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Component Features</h3>
          
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            {/* Feature 1 */}
            <div className="bg-white p-4 rounded-lg border border-indigo-100">
              <h4 className="font-bold text-lg text-indigo-600 mb-3">📌 Part 1: Category Header</h4>
              <ul className="space-y-2 text-gray-700">
                <li>✓ Main category title</li>
                <li>✓ "View More" button with callback</li>
                <li>✓ Responsive typography</li>
              </ul>
            </div>

            {/* Feature 2 */}
            <div className="bg-white p-4 rounded-lg border border-indigo-100">
              <h4 className="font-bold text-lg text-indigo-600 mb-3">📂 Part 2: Subcategories</h4>
              <ul className="space-y-2 text-gray-700">
                <li>✓ Grid layout with icons</li>
                <li>✓ Hover animations</li>
                <li>✓ Auto-responsive columns</li>
              </ul>
            </div>

            {/* Feature 3 */}
            <div className="bg-white p-4 rounded-lg border border-indigo-100">
              <h4 className="font-bold text-lg text-indigo-600 mb-3">📦 Part 3: Products</h4>
              <ul className="space-y-2 text-gray-700">
                <li>✓ Product image with discount badge</li>
                <li>✓ Price with currency formatting</li>
                <li>✓ Star ratings & review count</li>
              </ul>
            </div>

            {/* Feature 4 */}
            <div className="bg-white p-4 rounded-lg border border-indigo-100">
              <h4 className="font-bold text-lg text-indigo-600 mb-3">🎨 Design & UX</h4>
              <ul className="space-y-2 text-gray-700">
                <li>✓ Mobile responsive</li>
                <li>✓ Smooth hover effects</li>
                <li>✓ Loading & error states</li>
              </ul>
            </div>
          </div>
        </div>

        {/* Usage Instructions */}
        <div className="bg-gray-50 rounded-lg p-8 mt-12 border border-gray-200">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">How to Use</h3>
          
          <div className="space-y-4">
            <div>
              <h4 className="font-bold text-lg text-gray-900 mb-2">1. Import the component</h4>
              <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto text-sm">
{`import CategoryProductList from './components/CategoryProductList';`}
              </pre>
            </div>

            <div>
              <h4 className="font-bold text-lg text-gray-900 mb-2">2. Use in your page</h4>
              <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto text-sm">
{`<CategoryProductList
  categoryId={1}
  categoryName="Điện tử & Công nghệ"
  onViewMore={(id, name) => {
    // Handle navigation or actions
    navigate(\`/category/\${id}\`);
  }}
/>`}
              </pre>
            </div>

            <div>
              <h4 className="font-bold text-lg text-gray-900 mb-2">3. Or use the container component</h4>
              <pre className="bg-gray-900 text-gray-100 p-4 rounded overflow-x-auto text-sm">
{`import HomeCategorySection from './components/HomeCategorySection';

// This automatically loads all categories
<HomeCategorySection />`}
              </pre>
            </div>
          </div>
        </div>

        {/* Props Documentation */}
        <div className="bg-blue-50 rounded-lg p-8 mt-12 border border-blue-200">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Component Props</h3>
          
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead className="bg-blue-100">
                <tr>
                  <th className="px-4 py-3 font-bold">Prop</th>
                  <th className="px-4 py-3 font-bold">Type</th>
                  <th className="px-4 py-3 font-bold">Required</th>
                  <th className="px-4 py-3 font-bold">Description</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-blue-200">
                <tr>
                  <td className="px-4 py-3 font-mono text-sm">categoryId</td>
                  <td className="px-4 py-3 text-sm">number</td>
                  <td className="px-4 py-3 text-sm">✓ Yes</td>
                  <td className="px-4 py-3 text-sm">Main category ID (level 0)</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 font-mono text-sm">categoryName</td>
                  <td className="px-4 py-3 text-sm">string</td>
                  <td className="px-4 py-3 text-sm">✓ Yes</td>
                  <td className="px-4 py-3 text-sm">Display name of category</td>
                </tr>
                <tr>
                  <td className="px-4 py-3 font-mono text-sm">onViewMore</td>
                  <td className="px-4 py-3 text-sm">function</td>
                  <td className="px-4 py-3 text-sm">No</td>
                  <td className="px-4 py-3 text-sm">Callback when "View More" clicked</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Files Created */}
        <div className="bg-green-50 rounded-lg p-8 mt-12 border border-green-200">
          <h3 className="text-2xl font-bold text-gray-900 mb-6">Files Created</h3>
          
          <ul className="space-y-2 text-gray-700">
            <li className="flex items-start gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span><code className="bg-gray-100 px-2 py-1 rounded">CategoryProductList.jsx</code> - Main component</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span><code className="bg-gray-100 px-2 py-1 rounded">CategoryProductList.css</code> - Complete styling with responsive design</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span><code className="bg-gray-100 px-2 py-1 rounded">HomeCategorySection.jsx</code> - Container component for all categories</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span><code className="bg-gray-100 px-2 py-1 rounded">useCategoryProducts.js</code> - Custom hook for API integration</span>
            </li>
            <li className="flex items-start gap-3">
              <span className="text-green-600 font-bold">✓</span>
              <span><code className="bg-gray-100 px-2 py-1 rounded">CATEGORY_PRODUCT_LIST_README.md</code> - Full documentation</span>
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
}
