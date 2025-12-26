// import { useEffect, useState } from "react";
// import { useSearchParams } from "react-router-dom";
// // import { fetchSimilarProducts } from "../services/productServices";
// import ProductCard from "../components/ProductCard";

// export default function Results() {
//   const [params] = useSearchParams();
//   const query = params.get("query");
//   const [products, setProducts] = useState([]);
//   const [loading, setLoading] = useState(true);

//   useEffect(() => {
//     async function load() {
//       const res = await fetchSimilarProducts(query);
//       setProducts(res);
//       setLoading(false);
//     }
//     load();
//   }, [query]);

//   if (loading)
//     return <div className="text-center mt-10">Đang tải kết quả...</div>;

//   return (
//     <div className="p-6">
//       <h2 className="text-2xl font-semibold mb-4">
//         Kết quả gợi ý cho: <span className="text-blue-600">{query}</span>
//       </h2>
//       <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-4">
//         {products.map((p) => (
//           <ProductCard key={p.id} product={p} />
//         ))}
//       </div>
//     </div>
//   );
// }
