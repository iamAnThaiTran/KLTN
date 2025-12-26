import axios from "axios";

const API_URL = "http://localhost:5000/api/products";
const fakeData = [
    {
        "id": "shd1585b",
        "name": "Nồi áp suất điện tử Sunhouse Mama SHD1585B - 5 lít",
        "description": "Nồi áp suất điện tử dung tích 5 lít",
        "price": 1375000,
        "image_url": "https://example.com/images/shd1585b.jpg",
        "product_url": "https://example.com/products/shd1585b"
    },
    {
        "id": "kf-fl702ii",
        "name": "Bếp từ đôi Kaff KF-FL702II New Plus",
        "description": "Bếp từ đôi công suất cao",
        "price": 7200000,
        "image_url": "https://example.com/images/kf-fl702ii.jpg",
        "product_url": "https://example.com/products/kf-fl702ii"
    },
    {
        "id": "crp-jhr1060fd",
        "name": "Nồi cơm điện cao tần Cuckoo CRP-JHR1060FD - 1.8L",
        "description": "Nồi cơm điện cao tần dung tích 1.8L",
        "price": 6000000,
        "image_url": "https://example.com/images/crp-jhr1060fd.jpg",
        "product_url": "https://example.com/products/crp-jhr1060fd"
    },
    {
        "id": "cr1021",
        "name": "Nồi cơm điện Cuckoo CR1021 (CR-1021) - Nồi cơm điện cơ - 1 lít",
        "description": "Nồi cơm điện cơ dung tích 1 lít",
        "price": 452000,
        "image_url": "https://example.com/images/cr1021.jpg",
        "product_url": "https://example.com/products/cr1021"
    },
    {
        "id": "sms82eu88e",
        "name": "Máy rửa chén độc lập có sấy khô Eurosun SMS82EU88E",
        "description": "Máy rửa chén có chức năng sấy khô",
        "price": 15700000,
        "image_url": "https://example.com/images/sms82eu88e.jpg",
        "product_url": "https://example.com/products/sms82eu88e"
    },
    {
        "id": "kg65a3",
        "name": "Cây nước nóng lạnh Kangaroo KG65A3",
        "description": "Cây nước nóng lạnh tiện dụng",
        "price": 4600000,
        "image_url": "https://example.com/images/kg65a3.jpg",
        "product_url": "https://example.com/products/kg65a3"
    }
]


export async function fetchSimilarProducts(query) {
    //const res = await axios.get(`${API_URL}?query=${encodeURIComponent(query)}`);
    //   return res.data; 
    return fakeData;
}