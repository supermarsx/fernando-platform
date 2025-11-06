from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, Dict, Any, List
import json

app = FastAPI(title="OpenAI Proxy Server", version="1.0.0")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatCompletionRequest(BaseModel):
    model: str = "gpt-4"
    messages: List[ChatMessage]
    temperature: Optional[float] = 0.1
    max_tokens: Optional[int] = 1000
    stream: Optional[bool] = False

class EmbeddingRequest(BaseModel):
    input: str
    model: str = "text-embedding-ada-002"

class ImageRequest(BaseModel):
    prompt: str
    size: Optional[str] = "1024x1024"
    n: Optional[int] = 1

@app.post("/openai/chat/completions")
async def chat_completions(request: ChatCompletionRequest):
    """Handle Chat Completions through proxy"""
    try:
        # Extract text from messages for processing
        full_text = ""
        for message in request.messages:
            if message.role == "user":
                full_text += message.content + " "
        
        # Mock processing based on prompt content
        if "extract" in full_text.lower() or "invoice" in full_text.lower():
            # Return mock extraction result
            response = {
                "id": "chatcmpl-mock-123456789",
                "object": "chat.completion",
                "created": 1699000000,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": json.dumps({
                            "supplier_name": "Empresa Teste Lda",
                            "supplier_nif": "123456789",
                            "invoice_date": "15/10/2025",
                            "invoice_number": "2025/1234",
                            "subtotal": "875.00",
                            "vat_amount": "201.25",
                            "total_amount": "1076.25",
                            "vat_rate": "23",
                            "currency": "EUR"
                        })
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(full_text.split()) * 2,
                    "completion_tokens": 150,
                    "total_tokens": len(full_text.split()) * 2 + 150
                }
            }
        else:
            # Return general chat response
            response = {
                "id": "chatcmpl-mock-123456789",
                "object": "chat.completion",
                "created": 1699000000,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": "I understand your request and I'm ready to help you process documents."
                    },
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": len(full_text.split()) * 2,
                    "completion_tokens": 50,
                    "total_tokens": len(full_text.split()) * 2 + 50
                }
            }
        
        return {
            "success": True,
            "data": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/openai/embeddings")
async def embeddings(request: EmbeddingRequest):
    """Handle Embeddings through proxy"""
    try:
        # Mock embedding response
        embedding_vector = [0.1] * 1536  # Standard embedding dimension
        
        response = {
            "object": "list",
            "data": [{
                "object": "embedding",
                "index": 0,
                "embedding": embedding_vector
            }],
            "model": request.model,
            "usage": {
                "prompt_tokens": len(request.input.split()),
                "total_tokens": len(request.input.split())
            }
        }
        
        return {
            "success": True,
            "data": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/openai/images")
async def images(request: ImageRequest):
    """Handle Image generation through proxy"""
    try:
        # Mock image generation response
        image_urls = []
        for i in range(request.n):
            image_urls.append({
                "url": f"https://oaidalleapiprodscus.blob.core.windows.net/private/generated_image_{i}.png"
            })
        
        response = {
            "created": 1699000000,
            "data": image_urls
        }
        
        return {
            "success": True,
            "data": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/openai/models")
async def list_models():
    """List available models"""
    try:
        models = {
            "object": "list",
            "data": [
                {
                    "id": "gpt-4",
                    "object": "model",
                    "created": 1679000000,
                    "owned_by": "openai"
                },
                {
                    "id": "gpt-3.5-turbo",
                    "object": "model", 
                    "created": 1679000000,
                    "owned_by": "openai"
                },
                {
                    "id": "text-embedding-ada-002",
                    "object": "model",
                    "created": 1679000000,
                    "owned_by": "openai"
                }
            ]
        }
        
        return {
            "success": True,
            "data": models
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/openai/files")
async def upload_file():
    """Handle file upload (mock implementation)"""
    try:
        response = {
            "id": "file-mock-123456789",
            "object": "file",
            "bytes": 1024,
            "created_at": 1699000000,
            "filename": "uploaded_file.jsonl",
            "purpose": "fine-tune"
        }
        
        return {
            "success": True,
            "data": response
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health_check():
    return {"status": "healthy", "service": "openai-proxy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("openai_proxy:app", host="0.0.0.0", port=8006, reload=True)