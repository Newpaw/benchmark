from fastapi import FastAPI
from api import router

app = FastAPI(
    title="LLM Benchmark API",
    description="A REST API for benchmarking LLM endpoints with configurable parameters and Basic Authentication.",
    version="1.0.0"
)

app.include_router(router)

@app.get("/")
def read_root():
    return {"message": "LLM Benchmark API is running."}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
