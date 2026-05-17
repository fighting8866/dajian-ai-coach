from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api import session, result, ppt, qa, report, audio, vision, document, system, auth, profile
from database.db import init_db

app = FastAPI(
    title="答见AI教练API",
    description="AI辅助答辩/演讲训练助手",
    version="1.0.0"
)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(session.router, prefix="/api/session", tags=["session"])
app.include_router(result.router, prefix="/api", tags=["result"])
app.include_router(ppt.router, prefix="/api/ppt", tags=["ppt"])
app.include_router(qa.router, prefix="/api", tags=["qa"])
app.include_router(report.router, prefix="/api", tags=["report"])
app.include_router(audio.router, prefix="/api", tags=["audio"])
app.include_router(vision.router, prefix="/api", tags=["vision"])
app.include_router(document.router, prefix="/api/document", tags=["document"])
app.include_router(system.router, prefix="/api", tags=["system"])
app.include_router(auth.router, prefix="/api/auth", tags=["auth"])
app.include_router(profile.router, prefix="/api/profile", tags=["profile"])

# 启动时初始化数据库
@app.on_event("startup")
async def startup_event():
    init_db()
    paths_methods = []
    for route in app.routes:
        try:
            p = getattr(route, "path", "") or ""
            m = getattr(route, "methods", None) or set()
            paths_methods.append((p, m))
        except Exception:
            pass
    has_gen = any(p == "/api/qa/generate" for p, _ in paths_methods)
    has_fu = any(p == "/api/qa/followup" for p, _ in paths_methods)
    print(
        "[backend.boot] has_qa_generate_route=",
        has_gen,
        "has_qa_followup_route=",
        has_fu,
        flush=True,
    )

@app.get("/")
def root():
    return {"message": "答见AI教练API服务"}

@app.get("/health")
def health_check():
    from factories.provider_factory import get_ai_provider_status

    prov = get_ai_provider_status()
    return {
        "status": "ok",
        "service": "dajian-ai-coach-backend",
        "speech_provider": prov["speech_provider"],
        "vision_provider": prov["vision_provider"],
        "ascend_base_url": prov["ascend_base_url"],
        "document_parser_provider": prov.get("document_parser_provider"),
        "providers": prov,
        "hint": "训练前自检可 GET /api/system/provider-status（含 ascend_health_check.reachable）；本接口用于轻量连通性探测",
    }

print("=== REGISTERED ROUTES ===")
for route in app.routes:
    try:
        print(route.path, route.methods)
    except Exception:
        pass
print("=========================")