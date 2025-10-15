#!/usr/bin/env python3
"""
Mock Analysis Server for testing online mode

This server provides mock responses for the analysis API endpoints
to test the crawler's online mode functionality.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import time
import random
import asyncio

app = FastAPI(title="Mock Analysis API", version="1.0.0")

class AnalysisRequest(BaseModel):
    video_id: str
    title: str
    description: str
    channel_title: str
    duration: Optional[float] = 0.0
    audio_path: Optional[str] = ""
    tags: List[str] = []
    view_count: int = 0
    published_at: Optional[str] = ""

class AnalysisResponse(BaseModel):
    is_child_voice: bool
    confidence: float
    metadata: Dict[str, Any]

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "timestamp": time.time()}

@app.post("/analyze", response_model=AnalysisResponse)
async def analyze_video(request: AnalysisRequest):
    """
    Mock analysis endpoint that simulates voice classification.

    Randomly returns child voice detection with varying confidence.
    """
    # Simulate processing time
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # Mock analysis result - randomly determine if it's child voice
    is_child_voice = random.choice([True, False])

    # Generate confidence score
    if is_child_voice:
        confidence = random.uniform(0.7, 0.95)  # High confidence for children
    else:
        confidence = random.uniform(0.3, 0.8)   # Lower confidence for adults

    # Mock metadata
    metadata = {
        "processing_time": random.uniform(0.1, 0.5),
        "model_version": "mock-1.0.0",
        "audio_quality": random.choice(["high", "medium", "low"]),
        "language_detected": random.choice(["vi", "en", "unknown"])
    }

    return AnalysisResponse(
        is_child_voice=is_child_voice,
        confidence=round(confidence, 3),
        metadata=metadata
    )

@app.get("/")
async def root():
    """Root endpoint with API information."""
    return {
        "message": "Mock Analysis API Server",
        "version": "1.0.0",
        "endpoints": {
            "GET /health": "Health check",
            "POST /analyze": "Analyze video for child voice",
            "GET /": "This information"
        }
    }

if __name__ == "__main__":
    import uvicorn
    import asyncio

    print("Starting Mock Analysis Server on http://localhost:8002")
    print("Press Ctrl+C to stop")

    uvicorn.run(
        "mock_server:app",
        host="localhost",
        port=8002,
        reload=False,
        log_level="info"
    )