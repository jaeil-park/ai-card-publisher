"""쿠팡 파트너스 공식 오픈 API — 상품 검색 (HMAC-SHA256 CEA 인증).
주간 추천템 카드뉴스(weekly_picks)에서 급상승 카테고리의 실제 상품 후보를 가져오는 용도.
"""
import hashlib
import hmac
import os
import time
import urllib.parse

import requests

_DOMAIN = "https://api-gateway.coupang.com"
_SEARCH_PATH = "/v2/providers/affiliate_open_api/apis/openapi/products/search"


def _auth(method: str, path_with_query: str) -> str:
    access_key = os.environ.get("COUPANG_ACCESS_KEY", "")
    secret_key = os.environ.get("COUPANG_SECRET_KEY", "")
    path, _, query = path_with_query.partition("?")
    signed_date = time.strftime("%y%m%d", time.gmtime()) + "T" + time.strftime("%H%M%S", time.gmtime()) + "Z"
    message = signed_date + method + path + query
    signature = hmac.new(secret_key.encode(), message.encode(), hashlib.sha256).hexdigest()
    return f"CEA algorithm=HmacSHA256, access-key={access_key}, signed-date={signed_date}, signature={signature}"


def search_products(keyword: str, limit: int = 5) -> list[dict]:
    """키워드로 쿠팡 상품 검색. 반환: [{name, price, image_url, product_url, is_rocket}]"""
    if not os.environ.get("COUPANG_ACCESS_KEY") or not os.environ.get("COUPANG_SECRET_KEY"):
        print("⚠️ COUPANG_ACCESS_KEY/SECRET 미설정 — 쿠팡 상품 검색 스킵")
        return []

    query = urllib.parse.urlencode({"keyword": keyword, "limit": limit})
    path_with_query = f"{_SEARCH_PATH}?{query}"
    try:
        res = requests.get(
            _DOMAIN + path_with_query,
            headers={"Authorization": _auth("GET", path_with_query), "Content-Type": "application/json"},
            timeout=10,
        )
        res.raise_for_status()
        data = res.json()
        if str(data.get("rCode", "0")) != "0":
            print(f"⚠️ 쿠팡 검색 rCode={data.get('rCode')} {data.get('rMessage')}")
            return []
        products = data.get("data", {}).get("productData", []) or []
        return [
            {
                "name": p.get("productName", ""),
                "price": p.get("productPrice", 0),
                "image_url": p.get("productImage", ""),
                "product_url": p.get("productUrl", ""),
                "is_rocket": p.get("isRocket", False),
            }
            for p in products
        ]
    except Exception as e:
        print(f"⚠️ 쿠팡 상품 검색 실패: {e}")
        return []
