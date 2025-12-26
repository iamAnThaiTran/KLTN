import { BrowserRouter, Route, Routes } from "react-router-dom";
import Home from "../pages/Home";
import ProductDetailPage from "../common/ProductPageDetail";


export default function AppRouter() {
    return (
        <BrowserRouter>
            <Routes>
                <Route path="/" element={<Home />} />
                {/* <Route path="/results" element={<Results />} /> */}
                <Route path="/product/:title" element={<ProductDetailPage />} />
            </Routes>
        </BrowserRouter>
    )
}