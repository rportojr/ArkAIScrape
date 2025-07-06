#!/usr/bin/env python3
"""
AI Company Data Crawler - Web Application
Real-time monitoring and CSV processing interface
"""

import asyncio
import json
import os
import time
import uuid
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

import aiofiles
import pandas as pd
from fastapi import FastAPI, File, UploadFile, WebSocket, WebSocketDisconnect, HTTPException, Request
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel

# Import our existing crawler
from ai_server import CompanyCrawler, CompanyData

# Web app setup
app = FastAPI(title="AI Company Data Crawler - Web Interface", version="1.0.0")

# Create directories
Path("static").mkdir(exist_ok=True)
Path("templates").mkdir(exist_ok=True)
Path("uploads").mkdir(exist_ok=True)
Path("downloads").mkdir(exist_ok=True)

# Static files and templates
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Global state management
active_jobs: Dict[str, dict] = {}
websocket_connections: Dict[str, WebSocket] = {}

class JobStatus(BaseModel):
    job_id: str
    status: str  # pending, processing, completed, failed
    total_companies: int
    processed_companies: int
    success_count: int
    failure_count: int
    current_company: str
    start_time: float
    end_time: Optional[float] = None
    results: List[dict] = []
    error_message: Optional[str] = None

class WebCrawler:
    def __init__(self):
        self.crawler = CompanyCrawler()
        
    async def initialize(self):
        """Initialize the crawler"""
        await self.crawler.initialize_session()
        
    async def process_companies_with_updates(self, companies_df: pd.DataFrame, job_id: str):
        """Process companies with real-time updates"""
        total_companies = len(companies_df)
        
        # Initialize job status
        active_jobs[job_id] = JobStatus(
            job_id=job_id,
            status="processing",
            total_companies=total_companies,
            processed_companies=0,
            success_count=0,
            failure_count=0,
            current_company="",
            start_time=time.time(),
            results=[]
        )
        
        try:
            for idx, row in companies_df.iterrows():
                # Extract company info
                company_name = str(row.get('Company Name', row.get('Company', ''))).strip()
                website = str(row.get('Website', '')).strip()
                
                if not company_name or company_name.lower() in ['nan', 'none']:
                    continue
                
                # Update current status
                active_jobs[job_id].current_company = company_name
                await self.broadcast_update(job_id)
                
                # Process company
                start_time = time.time()
                try:
                    result = await self.crawler.process_company(company_name, website)
                    processing_time = time.time() - start_time
                    
                    # Convert to dict for JSON serialization
                    result_dict = {
                        'company_name': result.company_name,
                        'website': result.website,
                        'phone_number': result.phone_number,
                        'street_address': result.street_address,
                        'city': result.city,
                        'state': result.state,
                        'zip_code': result.zip_code,
                        'facebook_page': result.facebook_page,
                        'facebook_page_name': result.facebook_page_name,
                        'facebook_likes': result.facebook_likes,
                        'facebook_about': result.facebook_about,
                        'linkedin_page': result.linkedin_page,
                        'public_email': result.public_email,
                        'contact_person': result.contact_person,
                        'processing_time': processing_time,
                        'status': result.status,
                        'last_updated': result.last_updated
                    }
                    
                    # Update counters
                    if result.status == "Success":
                        active_jobs[job_id].success_count += 1
                    else:
                        active_jobs[job_id].failure_count += 1
                        
                    active_jobs[job_id].results.append(result_dict)
                    active_jobs[job_id].processed_companies += 1
                    
                except Exception as e:
                    # Handle individual company errors
                    error_result = {
                        'company_name': company_name,
                        'website': website,
                        'phone_number': '',
                        'street_address': '',
                        'city': '',
                        'state': '',
                        'zip_code': '',
                        'facebook_page': '',
                        'facebook_page_name': '',
                        'facebook_likes': '',
                        'facebook_about': '',
                        'linkedin_page': '',
                        'public_email': '',
                        'contact_person': '',
                        'processing_time': time.time() - start_time,
                        'status': f"Error: {str(e)}",
                        'last_updated': datetime.now().isoformat()
                    }
                    
                    active_jobs[job_id].results.append(error_result)
                    active_jobs[job_id].failure_count += 1
                    active_jobs[job_id].processed_companies += 1
                
                # Broadcast update
                await self.broadcast_update(job_id)
                
                # Small delay between companies
                await asyncio.sleep(1)
            
            # Mark as completed
            active_jobs[job_id].status = "completed"
            active_jobs[job_id].end_time = time.time()
            active_jobs[job_id].current_company = "Processing completed"
            await self.broadcast_update(job_id)
            
        except Exception as e:
            # Mark as failed
            active_jobs[job_id].status = "failed"
            active_jobs[job_id].error_message = str(e)
            active_jobs[job_id].end_time = time.time()
            await self.broadcast_update(job_id)
    
    async def broadcast_update(self, job_id: str):
        """Broadcast job update to connected websockets"""
        if job_id in active_jobs:
            job_data = active_jobs[job_id]
            message = {
                "type": "job_update",
                "job_id": job_id,
                "status": job_data.status,
                "total_companies": job_data.total_companies,
                "processed_companies": job_data.processed_companies,
                "success_count": job_data.success_count,
                "failure_count": job_data.failure_count,
                "current_company": job_data.current_company,
                "progress_percentage": round((job_data.processed_companies / job_data.total_companies) * 100, 1) if job_data.total_companies > 0 else 0,
                "processing_time": time.time() - job_data.start_time,
                "error_message": job_data.error_message,
                "results": job_data.results
            }
            
            # Send to all connected websockets
            disconnected = []
            for ws_id, websocket in websocket_connections.items():
                try:
                    await websocket.send_text(json.dumps(message))
                except:
                    disconnected.append(ws_id)
            
            # Clean up disconnected websockets
            for ws_id in disconnected:
                websocket_connections.pop(ws_id, None)

# Initialize crawler
web_crawler = WebCrawler()

@app.on_event("startup")
async def startup_event():
    """Initialize crawler on startup"""
    await web_crawler.initialize()

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Main web interface"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Upload CSV file and start processing"""
    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=400, detail="File must be a CSV")
    
    # Generate unique job ID
    job_id = str(uuid.uuid4())
    
    try:
        # Save uploaded file
        upload_path = Path("uploads") / f"{job_id}_{file.filename}"
        async with aiofiles.open(upload_path, 'wb') as f:
            content = await file.read()
            await f.write(content)
        
        # Read and validate CSV
        df = pd.read_csv(upload_path)
        
        # Validate required columns
        required_columns = ['Company', 'Company Name']
        if not any(col in df.columns for col in required_columns):
            raise HTTPException(
                status_code=400, 
                detail=f"CSV must contain 'Company' or 'Company Name' column. Found: {list(df.columns)}"
            )
        
        # Start processing in background
        asyncio.create_task(web_crawler.process_companies_with_updates(df, job_id))
        
        return {
            "job_id": job_id,
            "filename": file.filename,
            "total_companies": len(df),
            "message": "Processing started"
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

@app.get("/job-status/{job_id}")
async def get_job_status(job_id: str):
    """Get current job status"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    return {
        "job_id": job_id,
        "status": job.status,
        "total_companies": job.total_companies,
        "processed_companies": job.processed_companies,
        "success_count": job.success_count,
        "failure_count": job.failure_count,
        "current_company": job.current_company,
        "progress_percentage": round((job.processed_companies / job.total_companies) * 100, 1) if job.total_companies > 0 else 0,
        "processing_time": time.time() - job.start_time,
        "error_message": job.error_message
    }

@app.get("/download/{job_id}")
async def download_results(job_id: str, file_type: str = "all"):
    """Download processing results"""
    if job_id not in active_jobs:
        raise HTTPException(status_code=404, detail="Job not found")
    
    job = active_jobs[job_id]
    if job.status != "completed":
        raise HTTPException(status_code=400, detail="Job not completed yet")
    
    # Create DataFrame from results
    df = pd.DataFrame(job.results)
    
    if file_type == "success":
        df = df[df['status'] == 'Success']
        filename = f"success_results_{job_id}.csv"
    elif file_type == "failure":
        df = df[df['status'] != 'Success']
        filename = f"failure_results_{job_id}.csv"
    else:
        filename = f"all_results_{job_id}.csv"
    
    # Save file
    file_path = Path("downloads") / filename
    df.to_csv(file_path, index=False)
    
    return FileResponse(
        path=file_path,
        filename=filename,
        media_type='text/csv'
    )

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket for real-time updates"""
    await websocket.accept()
    ws_id = str(uuid.uuid4())
    websocket_connections[ws_id] = websocket
    
    try:
        while True:
            # Keep connection alive
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_connections.pop(ws_id, None)

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)