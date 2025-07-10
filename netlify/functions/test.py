import json

def handler(event, context):
    """Simple test function to verify Netlify functions are working"""
    
    return {
        'statusCode': 200,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
        'body': json.dumps({
            'message': 'Test function is working!',
            'timestamp': '2024-01-XX',
            'success': True
        })
    } 