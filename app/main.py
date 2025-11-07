#!/usr/bin/env python3
"""Main MCP server entry point."""
from mcp.server.fastmcp import FastMCP
from app.services.grok_service import GrokService
from app.services.s3_service import S3Service
from app.services.dynamodb_service import DynamoDBService
from app.models.analysis import AnalysisRequest, AnalysisResult
import os

# Initialize MCP server
mcp = FastMCP("Plant Disease Detection Server")

# Initialize services
grok_service = GrokService()
s3_service = S3Service()
dynamodb_service = DynamoDBService()

@mcp.tool()
def analyze_plant_image(s3_bucket: str, s3_key: str, user_prompt: str) -> str:
    """
    Analyze plant image from S3 storage with custom user prompt.
    
    Args:
        s3_bucket: S3 bucket name containing the plant image
        s3_key: S3 object key/path to the image file
        user_prompt: Custom analysis instructions from the user
        
    Returns:
        JSON string containing analysis results
    """
    try:
        # Download image from S3
        image_data = s3_service.download_image(s3_bucket, s3_key)
        
        # Analyze with Grok AI
        analysis_result = grok_service.analyze_image(image_data, user_prompt)
        
        # Save to DynamoDB
        saved_id = dynamodb_service.save_analysis(
            s3_bucket=s3_bucket,
            s3_key=s3_key,
            user_prompt=user_prompt,
            analysis_result=analysis_result
        )
        
        # Add metadata to response
        analysis_result['analysis_id'] = saved_id
        analysis_result['s3_location'] = f"s3://{s3_bucket}/{s3_key}"
        
        return analysis_result
        
    except Exception as e:
        return {
            "error": str(e),
            "s3_bucket": s3_bucket,
            "s3_key": s3_key
        }

@mcp.tool()
def get_analysis(analysis_id: str) -> str:
    """
    Retrieve previous plant analysis results by ID.
    
    Args:
        analysis_id: Unique identifier for the analysis
        
    Returns:
        JSON string containing stored analysis results
    """
    try:
        return dynamodb_service.get_analysis(analysis_id)
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    mcp.run()