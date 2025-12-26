export default function ProductCard({ product }) {
  return (
    <div
      
      onClick={() => window.open(product.url, "_blank")}
    >
      <img src={product.image} alt={product.name} />
      <h3 >{product.name}</h3>
      <p >{product.price}</p>
      <span >{product.source}</span>
    </div>
  );
}