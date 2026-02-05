from fastapi import FastAPI

app = FastAPI(title="Railway FastAPI Demo")


@app.get("/")
def read_root():
    return {"message": "Hello from FastAPI on Railway"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.get("/echo/{text}")
def echo(text: str):
    return {"echo": text}
