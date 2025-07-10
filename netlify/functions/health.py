import json
from datetime import datetime

def handler(event, context):
    """Health check endpoint for Netlify deployment"""
    
    health_data = {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "environment": "netlify",
        "function": "health"
    }
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps(health_data)
    } 