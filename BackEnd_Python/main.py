from fastapi import FastAPI
from pydantic import BaseModel
from openai import OpenAI
import os
from dotenv import load_dotenv

load_dotenv()
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()


class QueryInput(BaseModel):
    description: str


class QueryOutput(BaseModel):
    keywords: list
    categories: list
    product_suggestions: list


def extract_keywords(description: str):
    """
    Gọi LLM để phân tích mô tả → sinh từ khóa tìm kiếm sản phẩm.
    """
    prompt = f"""
    Phân tích mô tả sau và trả về:
    - danh sách từ khóa tìm sản phẩm
    - danh mục sản phẩm++++++++++++++++
    - sản phẩm gợi ý (dạng text)
    Chỉ trả về JSON.

    Mô tả: "{description}"
    """

    resp = client.chat.completions.create(
        model="gpt-4o-mini",     # hoặc gpt-4o
        messages=[{"role": "user", "content": prompt}],
        temperature=0.1
    )

    return resp.choices[0].message["content"]


@app.post("/search", response_model=QueryOutput)
def search_products(payload: QueryInput):
    """
    Nhận mô tả → LLM phân tích → trả về keywords để search trên Shopee/Lazada/Tiki.
    """
    raw = extract_keywords(payload.description)

    # JSON trả về từ LLM, ví dụ:
    # {"keywords": ["đèn ngủ pastel","quà tặng bạn gái"], "categories":["decor","lifestyle"], "product_suggestions":["Đèn ngủ Aroma","Nến thơm pastel"]}

    import json
    parsed = json.loads(raw)

    return QueryOutput(
        keywords=parsed.get("keywords", []),
        categories=parsed.get("categories", []),
        product_suggestions=parsed.get("product_suggestions", [])
    )


@app.get("/")
def root():
    return {"message": "Product search backend running!"}
