// Footer.jsx
import React from 'react';
// Nếu bạn dùng icon từ react-icons
// import { FaFacebookF } from 'react-icons/fa';

const Footer = () => {
  return (
    <footer className="bg-[#f5f5f5] text-[#333] text-sm">
      {/* Phần chính - 3 cột */}
      <div className="max-w-7xl mx-auto px-4 py-10 md:py-12 grid grid-cols-1 md:grid-cols-3 gap-8 border-b border-gray-300">
        {/* Cột 1 - Hỗ trợ khách hàng */}
        <div>
          <h3 className="font-bold text-base mb-4 uppercase">Hỗ trợ khách hàng</h3>
          <ul className="space-y-2">
            <li>
              <a href="/hotline" className="hover:underline">Hotline: 096.789.5454</a>
            </li>
            <li>
              <a href="mailto:contact@websosanh.vn" className="hover:underline">
                Email: contact@websosanh.vn
              </a>
            </li>
            <li>
              <a href="/cau-hoi-thuong-gap" className="hover:underline">
                Các câu hỏi thường gặp
              </a>
            </li>
            <li>
              <a href="/chinh-sach-ban-hang" className="hover:underline">
                Chính sách bán hàng
              </a>
            </li>
            <li>
              <a href="/chinh-sach-thuong-hang" className="hover:underline">
                Chính sách thương hiệu
              </a>
            </li>
          </ul>
        </div>

        {/* Cột 2 - Hợp tác & liên kết */}
        <div>
          <h3 className="font-bold text-base mb-4 uppercase">Hợp tác và liên kết</h3>
          <div className="mb-4">
            <a
              href="https://websosanh.vn/business.htm"
              className="inline-flex items-center gap-2 bg-red-600 text-white px-4 py-2 rounded hover:bg-red-700"
            >
              <span className="text-lg">Bán hàng cùng</span>
              <span className="font-bold">Websosanh</span>
            </a>
          </div>
          <ul className="space-y-2">
            <li>
              <a href="/kenh-tac-ban-hang" className="hover:underline">
                Kênh tác bán hàng
              </a>
            </li>
          </ul>
        </div>

        {/* Cột 3 - Kết nối với chúng tôi */}
        <div>
          <h3 className="font-bold text-base mb-4 uppercase">Kết nối với chúng tôi</h3>
          <div className="flex items-center gap-4">
            <a
              href="https://www.facebook.com/websosanh"
              target="_blank"
              rel="noopener noreferrer"
              className="text-blue-600 hover:text-blue-800 text-2xl"
              aria-label="Facebook Websosanh"
            >
              {/* <FaFacebookF /> */}f
            </a>
            {/* Bạn có thể thêm Zalo, YouTube... nếu có */}
          </div>
        </div>
      </div>

      {/* Phần thông tin công ty + bottom bar */}
      <div className="max-w-7xl mx-auto px-4 py-8 text-center md:text-left grid grid-cols-1 md:grid-cols-2 gap-6">
        <div>
          <p className="font-bold mb-2">CÔNG TY CỔ PHẦN SO SÁNH VIỆT NAM</p>
          <p>Trụ sở chính: Số 195 Khâm Thiên, Quận Đống Đa, Hà Nội</p>
          <p>Giấy chứng nhận đăng ký kinh doanh số 0106373516, cấp ngày 02/12/2013, cấp bởi Sở KH&ĐT TP. Hà Nội</p>
        </div>

        <div className="flex flex-col md:items-end space-y-2">
          <p>© 2013 - 2026 Bản quyền thuộc về Công ty cổ phần So Sánh Việt Nam</p>
          <div className="flex flex-wrap gap-4 justify-center md:justify-end">
            <img
              src="https://websosanh.vn/Content/images/bo-cong-thuong.png"
              alt="Bộ Công Thương"
              className="h-10"
            />
            <img
              src="https://websosanh.vn/Content/images/dk-bct.png"
              alt="Đã đăng ký Bộ Công Thương"
              className="h-10"
            />
            <img
              src="https://websosanh.vn/Content/images/dmca-protected.png"
              alt="DMCA Protected"
              className="h-10"
            />
            {/* Thêm các logo khác nếu bạn có link chính xác */}
          </div>
        </div>
      </div>
    </footer>
  );
};

export default Footer;