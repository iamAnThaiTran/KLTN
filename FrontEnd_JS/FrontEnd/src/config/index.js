export const API_BASE_URL = 'http://localhost:8000';
 
export const CATEGORIES = [
  { icon: '👟', label: 'Giày đẹp' },
  { icon: '⌚', label: 'Đồng hồ thông minh' },
  { icon: '🎧', label: 'Tai nghe' },
  { icon: '📱', label: 'Điện thoại' },
  { icon: '🎒', label: 'Phụ kiện' },
  { icon: '🛍️', label: 'Accessories' },
];
 
export const QUICK_SEARCHES = [
  { icon: '👟', label: 'Giày chạy bộ' },
  { icon: '🎧', label: 'Tai nghe bluetooth' },
  { icon: '🎁', label: 'Quà sinh nhật cho bạn gái' },
  { icon: '⌚', label: 'Đồng hồ thông minh' },
];
 
export const POPULAR_PRODUCTS = [
  { name: 'Nike Air Force 1', price: '2.400.000đ', sales: null },
  { name: 'AirPods Pro 2', price: '5.300.000đ', sales: '630 ches' },
  { name: 'Xiaomi Redmi Watch 3', price: '1.890.000đ', sales: '410 ches' },
  { name: 'Song GaN 65W', price: '359.000đ', sales: '1670 ches' },
];
 
export const EXAMPLE_QUERIES = [
  'Giày Nike chạy bộ dưới 2 triệu',
  'Sneaker trắng size 42',
  'Tai nghe chống ồn tốt',
  'Quà sinh nhật cho bạn gái dưới 500K',
];
 


export const PERSONALIZED_DATA = {
  topics: ['giày chạy bộ', 'quà sinh nhật', 'tai nghe bluetooth'],
  products: [
    { name: 'Nike Pegasus 40', price: '2.900.000đ', img: 'https://static.nike.com/a/images/t_web_pdp_535_v2/f_auto,u_9ddf04c7-2a9a-4d76-add1-d15af8f0263d,c_scale,fl_relative,w_1.0,h_1.0,fl_layer_apply/1abaae51-d7c4-4ca6-8e2b-8133b90d168b/AIR+ZOOM+PEGASUS+40.png' },
    { name: 'AirPods Pro 2', price: '5.300.000đ', img: 'https://store.storeimages.cdn-apple.com/1/as-images.apple.com/is/airpods-pro-3-hero-select-202509?wid=976&hei=916&fmt=jpeg&qlt=90&.v=cmp4MmZ6OWxOeHNNTXh4SzlBNUpEb1RucE9zZTI5eEREaWZpY29lSld3eWVDYXovZDMyN1dXU211bjZoVlVUcWJGcXNRQnFCV0w3WVRjTExvdm1ic1YxRUxFRmRlWDBITzhnRmZ5OTRmaVdKTExiOEFsRmxtQ2Nua0tRSC83MkI' },
    { name: 'Gấu bông Teddy', price: '250.000đ', img: 'https://upload.bemori.vn/gau-bong-Teddy/teddy-fullsize/teddy-ao-len-co-ke/teddy-ao-len-co-ke-1.webp' },
    { name: 'Sony WF-1000XM5', price: '6.900.000đ', img: 'https://cdn2.cellphones.com.vn/insecure/rs:fill:0:358/q:90/plain/https://cellphones.com.vn/media/catalog/product/t/a/tai-nghe-khong-day-sony-wf-1000xm5-6_1.png' },
    { name: 'Nước hoa mini', price: '490.000đ', img: 'https://salt.tikicdn.com/cache/750x750/ts/product/7b/aa/08/579dc52a4175be1abe66ad46ececf9f6.jpg.webp' },
  ],
};

export const formatTopics = (topics) => {
  if (topics.length === 1) return topics[0];
  if (topics.length === 2) return `${topics[0]} và ${topics[1]}`;
  return `${topics.slice(0, -1).join(', ')} và ${topics[topics.length - 1]}`;
};