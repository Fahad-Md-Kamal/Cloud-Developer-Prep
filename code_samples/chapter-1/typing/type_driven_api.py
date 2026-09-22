from typing import TypedDict, Literal, Union, Annotated
from pydantic import BaseModel, Field, validator
from enum import Enum
from fastapi import FastAPI, HTTPException
import asyncio

# Precise type definitions for API responses
class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class ProcessingResult(TypedDict):
    document_id: str
    status: DocumentStatus
    extracted_text: str
    confidence_score: float
    processing_time_ms: int

# Pydantic models for request/response validation
class DocumentUploadRequest(BaseModel):
    url: str = Field(..., description="URL to crawl and process")
    jurisdiction: Literal["US", "UK", "EU", "CA"] = Field(..., description="Legal jurisdiction")
    document_type: Literal["statute", "regulation", "case_law"] = Field(..., description="Type of legal document")
    priority: Annotated[int, Field(ge=1, le=10)] = Field(5, description="Processing priority (1-10)")
    
    @validator('url')
    def validate_url(cls, v):
        if not v.startswith(('http://', 'https://')):
            raise ValueError('URL must start with http:// or https://')
        return v

class DocumentProcessingResponse(BaseModel):
    request_id: str
    status: DocumentStatus
    estimated_completion: int = Field(..., description="Estimated completion time in seconds")
    
    class Config:
        use_enum_values = True

# Type-safe service layer
class LegalDocumentService:
    async def submit_document(
        self, 
        request: DocumentUploadRequest
    ) -> DocumentProcessingResponse:
        """Submit a document for processing with full type safety"""
        
        # Process the request
        request_id = f"doc_{hash(request.url)}"
        
        # Simulate async processing
        await asyncio.sleep(0.1)
        
        return DocumentProcessingResponse(
            request_id=request_id,
            status=DocumentStatus.PENDING,
            estimated_completion=300
        )
    
    async def get_processing_result(
        self, 
        request_id: str
    ) -> Union[ProcessingResult, None]:
        """Get processing results with precise typing"""
        
        # Simulate database lookup
        await asyncio.sleep(0.05)
        
        if request_id.startswith("doc_"):
            return ProcessingResult(
                document_id=request_id,
                status=DocumentStatus.COMPLETED,
                extracted_text="Article 1: The legislature shall...",
                confidence_score=0.95,
                processing_time_ms=2500
            )
        
        return None

# FastAPI integration with automatic OpenAPI generation
app = FastAPI(title="Legal Document Processing API")
service = LegalDocumentService()

@app.post("/documents/submit", response_model=DocumentProcessingResponse)
async def submit_document(request: DocumentUploadRequest):
    """Submit a legal document for processing"""
    return await service.submit_document(request)

@app.get("/documents/{request_id}/result")
async def get_result(request_id: str) -> ProcessingResult:
    """Get processing results"""
    result = await service.get_processing_result(request_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return result

# Usage with full type checking
async def example_usage():
    service = LegalDocumentService()
    
    # Type-safe request creation
    request = DocumentUploadRequest(
        url="https://www.legislation.gov.uk/ukpga/2023/1",
        jurisdiction="UK",
        document_type="statute",
        priority=7
    )
    
    # Submit and get typed response
    response = await service.submit_document(request)
    print(f"Submitted with ID: {response.request_id}")
    
    # Get results with known types
    result = await service.get_processing_result(response.request_id)
    if result:
        print(f"Processing completed with {result['confidence_score']:.2%} confidence")

if __name__ == "__main__":
    asyncio.run(example_usage())
