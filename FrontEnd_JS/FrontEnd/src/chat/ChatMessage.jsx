import ProductCard from "../common/ProductCard";

function ChatMessage({ message }) {
  const isUser = message.type === 'user';
  
  return (
    <div className={`flex gap-3 mb-4 ${isUser ? 'justify-end' : 'justify-start'}`}>
      {!isUser && (
        <div className="w-8 h-8 bg-indigo-600 rounded-full flex items-center justify-center flex-shrink-0 text-white">
          🤖
        </div>
      )}
      <div
        className={`max-w-6xl rounded-2xl px-4 py-3 ${
          isUser
            ? 'bg-indigo-600 text-white'
            : 'bg-gray-100 text-gray-900'
        }`}
      >
        <p className="text-sm whitespace-pre-wrap">{message.content}</p>
        {message.products && message.products.length > 0 && (
          <div className="grid grid-cols-4 gap-3 mt-4">
            {message.products.map((product) => (
              <ProductCard key={product.id} product={product} onClick={() => {}} />
            ))}
          </div>
        )}
      </div>
      {isUser && (
        <div className="w-8 h-8 bg-indigo-200 rounded-full flex items-center justify-center flex-shrink-0">
          👤
        </div>
      )}
    </div>
  );
}

export default ChatMessage;