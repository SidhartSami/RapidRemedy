from fastapi import FastAPI
import os

app = FastAPI(title="Rapid Remedy API")

@app.get("/")
async def root():
    return {"message": "Rapid Remedy Backend is running"}

@app.get("/health")
async def health():
    return {"status": "healthy"}
