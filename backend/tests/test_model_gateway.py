import pytest
from httpx import AsyncClient
from app.services.model_gateway import ModelGatewayService


@pytest.mark.asyncio
async def test_model_gateway_direct_capabilities():
    gateway = ModelGatewayService()

    # 1. Chat Generation Capability
    chat_ans = await gateway.generate_chat("What is machine maintenance?")
    assert len(chat_ans) > 0

    # 2. Document & Query Embedding Capability
    q_vec = await gateway.embed_text("hydraulic pressure check")
    assert len(q_vec) == 1024

    doc_vecs = await gateway.embed_documents(["doc 1 content", "doc 2 content"])
    assert len(doc_vecs) == 2
    assert len(doc_vecs[0]) == 1024

    # 3. Cross-Encoder Reranking Capability
    docs = [
        "Recipe for baking chocolate cake",
        "Procedure for calibrating hydraulic pressure sensor ERR-404",
        "Weather forecast for tomorrow"
    ]
    reranked = await gateway.rerank_documents("ERR-404 hydraulic calibration", docs, top_k=2)
    assert len(reranked) == 2
    assert "ERR-404" in reranked[0].document_text
    assert reranked[0].score > 0.0

    # 4. Vision Analysis Capability
    img_analysis = await gateway.analyze_vision(b"fake_image_bytes", "Identify errors in image")
    assert "Analyzed image" in img_analysis or len(img_analysis) > 0

    # 5. OCR Text Extraction Capability
    ocr_text = await gateway.extract_ocr_text(b"fake_doc_image_bytes", "image/png")
    assert "OCR Text" in ocr_text or len(ocr_text) > 0


@pytest.mark.asyncio
async def test_models_api_endpoints(async_client: AsyncClient):
    # 1. Register Tenant & Login Admin
    reg = await async_client.post("/api/v1/auth/register", json={
        "tenant_name": "Gateway Tenant",
        "tenant_slug": "gateway-tenant",
        "admin_email": "admin@gateway-tenant.com",
        "admin_password": "GatewayPassword123!"
    })
    assert reg.status_code == 201

    login = await async_client.post("/api/v1/auth/login", json={
        "email": "admin@gateway-tenant.com",
        "password": "GatewayPassword123!",
        "tenant_slug": "gateway-tenant"
    })
    token = login.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # 2. Get Model Registry
    registry_res = await async_client.get("/api/v1/models", headers=headers)
    assert registry_res.status_code == 200
    reg_data = registry_res.json()
    assert len(reg_data) == 5
    capabilities = [m["capability"] for m in reg_data]
    assert "chat_generation" in capabilities
    assert "embedding" in capabilities
    assert "reranking" in capabilities
    assert "vision" in capabilities
    assert "ocr" in capabilities

    # 3. Rerank API Endpoint
    rerank_req = {
        "query": "PSI calibration pressure sensors",
        "documents": [
            "Calibration Guide for pressure sensors to 150 PSI",
            "General safety rules for office cafeteria"
        ],
        "top_k": 2
    }
    rerank_res = await async_client.post("/api/v1/models/rerank", json=rerank_req, headers=headers)
    assert rerank_res.status_code == 200
    rerank_data = rerank_res.json()
    assert len(rerank_data["results"]) == 2
    assert "PSI" in rerank_data["results"][0]["document_text"]

    # 4. OCR API Endpoint
    files = {"file": ("document_sample.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR", "image/png")}
    ocr_res = await async_client.post("/api/v1/models/ocr", files=files, headers=headers)
    assert ocr_res.status_code == 200
    ocr_data = ocr_res.json()
    assert "extracted_text" in ocr_data
