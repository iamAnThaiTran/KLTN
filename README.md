# Hệ thống thu thập, so sánh và gợi ý sản phẩm TMĐT

## Giới thiệu
Hệ thống hỗ trợ:
- Thu thập dữ liệu sản phẩm từ sàn TMĐT
- Phân tích yêu cầu người dùng bằng LLM
- Gợi ý loại sản phẩm và thuộc tính phù hợp
- So sánh sản phẩm theo mức độ tương đồng thuộc tính

---

## Công nghệ sử dụng
- Frontend: ReactJS + Vite
- Backend: FastAPI
- Database: PostgreSQL
- Docker & Docker Compose
- OpenAI API / GPT-4o mini

---

## Yêu cầu môi trường
- Docker
- Docker Compose

Kiểm tra:
```bash
docker --version
docker compose version
## Yêu cầu môi trường
- Docker
- Docker Compose

## Cách chạy hệ thống

### 1. Clone source code
```bash
git clone <repo-url>
cd <project-name>
```

### 2. Khởi động hệ thống
```bash
docker compose up --build
```

## Truy cập hệ thống
- Frontend: http://localhost:5173
- Backend API: http://localhost:8000