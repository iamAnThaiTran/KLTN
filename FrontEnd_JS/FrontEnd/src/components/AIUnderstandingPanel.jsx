import { Lightbulb } from 'lucide-react';

export default function AIUnderstandingPanel({ 
  understanding, 
  question, 
  options, 
  onSelectOption,
  isLoading 
}) {
  return (
    <div className="bg-gradient-to-r from-indigo-50 to-blue-50 border border-indigo-200 rounded-lg p-6 mb-6 mx-6 mt-4">
      {/* AI Understanding Header */}
      <div className="flex items-center gap-2 mb-4">
        <Lightbulb className="w-5 h-5 text-indigo-600" />
        <p className="text-sm font-semibold text-gray-800">
          {understanding || "Đang hiểu yêu cầu của bạn..."}
        </p>
      </div>

      {/* Question */}
      <h3 className="text-base font-semibold text-gray-900 mb-4">
        {question || "Bạn đang tìm kiếm gì?"}
      </h3>

      {/* Options Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
        {options && options.map((option, index) => (
          <button
            key={index}
            onClick={() => onSelectOption(option)}
            disabled={isLoading}
            className="px-4 py-3 bg-white border border-indigo-300 text-gray-800 rounded-lg hover:bg-indigo-50 hover:border-indigo-500 transition-all font-medium text-sm disabled:opacity-50 disabled:cursor-not-allowed active:scale-95"
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}
