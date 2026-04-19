from fastapi import FastAPI

# 建立 FastAPI app（API server）
app = FastAPI()


# =========================
# 💰 Payment Success Mock
# =========================
@app.post("/mock/payment/success")
def payment_success():
    # 模擬付款成功回應
    return {
        "status": "success",
        "message": "payment approved"
    }


# =========================
# ❌ Payment Fail Mock
# =========================
@app.post("/mock/payment/fail")
def payment_fail():
    # 模擬付款失敗回應
    return {
        "status": "failed",
        "message": "payment rejected"
    }