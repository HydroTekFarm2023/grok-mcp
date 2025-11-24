import logging
import json
import base64
import uuid
from datetime import datetime
from decimal import Decimal
from mcp.server.fastmcp import FastMCP
from app.config import DYNAMODB_TABLE_NAME, MODEL_ID, S3_BUCKET_NAME
from app.aws_clients import grok_client, dynamodb, s3_client
from app.prompt_text import PROMPT_TEXT

# Initialize FastMCP server
mcp = FastMCP("plant-disease-detection")

@mcp.tool()
async def detect_plant_disease(image_base64: str, user_prompt: str = "") -> dict:
    """
    Detects plant health condition, if unhealthy it will detect the disease and provide recommendations and preventions.
    
    Args:
        image_base64: Base64 encoded image string
        user_prompt: Additional instructions or context from the user
    """
    try:
        # Generate image key and upload to S3
        image_key = f"uploads/{uuid.uuid4()}.jpg"
        image_bytes = base64.b64decode(image_base64)
        s3_client.put_object(Bucket=S3_BUCKET_NAME, Key=image_key, Body=image_bytes)
        logging.info(f"Uploaded image to s3://{S3_BUCKET_NAME}/{image_key}")

        # Build the prompt
        full_prompt = PROMPT_TEXT
        if user_prompt:
            full_prompt += f"\n\nUser note: {user_prompt}"

        # Call Grok Vision API
        response = grok_client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": full_prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_base64}"},
                        },
                    ],
                }
            ],
            max_tokens=2000
        )

        content = response.choices[0].message.content

        # Parse JSON safely
        try:
            if "{" in content and "}" in content:
                json_start = content.find("{")
                json_end = content.rfind("}") + 1
                json_str = content[json_start:json_end]
                result = json.loads(json_str)
            else:
                result = {
                    "disease_detected": "ParsingError",
                    "health_status": "unknown",
                    "fungal_status": "unknown",
                    "plant_part": "unknown",
                    "recommendations": ["Failed to parse model output."],
                    "confidence_score": 0.0,
                }
        except Exception as e:
            result = {
                "disease_detected": "ParsingError",
                "health_status": "unknown",
                "fungal_status": "unknown",
                "plant_part": "unknown",
                "recommendations": [f"JSON parsing failed: {str(e)}"],
                "confidence_score": 0.0,
            }

        # Save to DynamoDB
        table = dynamodb.Table(DYNAMODB_TABLE_NAME)
        item = {
            "id": str(uuid.uuid4()),
            "image_key": image_key,
            "disease_detected": result.get("disease_detected", "Unknown"),
            "fungal_status": result.get("fungal_status", "Unknown"),
            "health_status": result.get("health_status", "Unknown"),
            "plant_part": result.get("plant_part", "Unknown"),
            "recommendations": result.get("recommendations", []),
            "confidence_score": Decimal(str(result.get("confidence_score", 0.0))),
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "user_prompt": user_prompt
        }

        table.put_item(Item=item)
        logging.info("Saved to DynamoDB")

        # Return result to client
        return result

    except Exception as e:
        logging.error(f"Error in detect_plant_disease: {str(e)}")
        return {
            "error": str(e),
            "health_status": "error",
            "disease_detected": "ProcessingError",
            "confidence_score": 0.0
        }

@mcp.tool()
async def analyze_s3_image(s3_bucket: str, s3_key: str, user_prompt: str = "") -> dict:
    """
    Analyze plant image from S3 bucket
    
    Args:
        s3_bucket: S3 bucket name
        s3_key: S3 object key
        user_prompt: Additional instructions from user
    """
    try:
        # Download image from S3
        response = s3_client.get_object(Bucket=s3_bucket, Key=s3_key)
        image_data = response['Body'].read()
        image_base64 = base64.b64encode(image_data).decode('utf-8')
        
        # Use the main detection function
        return await detect_plant_disease(image_base64, user_prompt)
        
    except Exception as e:
        return {
            "error": f"S3 download failed: {str(e)}",
            "health_status": "error",
            "confidence_score": 0.0
        }
    
@mcp.tool()
async def analyze_local_image(image_path: str, user_prompt: str = "") -> dict:
    """Analyze plant image from local file path"""
    try:
        with open(image_path, "rb") as f:
            image_bytes = f.read()
            image_base64 = base64.b64encode(image_bytes).decode('utf-8')
        return await detect_plant_disease(image_base64, user_prompt)
        
    except Exception as e:
        return {
            "error": f"Failed to read local image: {str(e)}",
            "health_status": "error",
            "confidence_score": 0.0
        }

if __name__ == "__main__":
    mcp.run()
