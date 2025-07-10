# Netlify Scheduled Functions Guide

## 🕐 Overview

This project uses Netlify's built-in scheduled functions feature for automatic background processing. No plugins or external services required!

## 📋 Scheduled Functions in This Project

### 1. **`scheduled-bucket-watcher.py`** 
- **Schedule**: Every 5 minutes (`*/5 * * * *`)
- **Purpose**: Monitors Supabase bucket for new resume uploads
- **Actions**: 
  - Checks for new files in `msmm-resumes` bucket
  - Downloads and processes new resumes
  - Parses resumes using OpenAI
  - Loads data into Supabase database
  - Handles trigger queue for immediate processing

### 2. **Additional Scheduled Functions**
You can add more scheduled functions by:
- Creating new `.py` files in `netlify/functions/`
- Adding the `config` export with schedule
- Following the same pattern as the bucket watcher

## 🔧 How It Works

### Function Structure
```python
def handler(event, context):
    """Main function logic"""
    return {
        'statusCode': 200,
        'body': json.dumps({"status": "success"})
    }

# Schedule configuration (required)
config = {
    "schedule": "*/5 * * * *"  # Cron syntax
}
```

### Schedule Options
```python
# Cron syntax examples
"*/5 * * * *"    # Every 5 minutes
"0 */2 * * *"    # Every 2 hours
"0 9 * * *"      # Daily at 9 AM
"0 9 * * 1"      # Weekly on Monday at 9 AM

# Netlify aliases
"@hourly"        # Every hour
"@daily"         # Every day at midnight
"@weekly"        # Every Sunday at midnight
"@monthly"       # First day of month at midnight
```

## 🚀 Deployment Process

### 1. Automatic Detection
- Netlify automatically detects functions with `config` export
- Functions are marked as "Scheduled" in the dashboard
- No manual configuration needed

### 2. Configuration in `netlify.toml`
```toml
[functions]
directory = "netlify/functions"
python_runtime = "python3.9"
timeout = 30
```

### 3. Verification After Deploy
1. Go to Netlify dashboard → Functions tab
2. Look for functions marked as **"Scheduled"**
3. Check function logs for execution history
4. Monitor for errors or warnings

## 📊 Monitoring Scheduled Functions

### In Netlify Dashboard
1. **Functions Tab**: Shows all scheduled functions
2. **Function Logs**: Real-time execution logs
3. **Function Metrics**: Execution count and duration

### Log Output Example
```
📅 2024-01-15T10:00:00Z - Scheduled bucket check started
📁 Found 2 new files to process: ['resume1.pdf', 'resume2.pdf']
🔄 Processing resume1.pdf...
✅ Successfully processed resume1.pdf
🔄 Processing resume2.pdf...
✅ Successfully processed resume2.pdf
✅ Scheduled bucket check completed: 2 processed, 0 errors
```

## 🛠️ Troubleshooting

### Common Issues

#### Functions Not Scheduling
- **Check**: Function has `config` export with `schedule`
- **Check**: Function deployed successfully
- **Check**: No syntax errors in function code

#### Functions Timing Out
- **Solution**: Increase timeout in `netlify.toml`
- **Solution**: Optimize function code for faster execution
- **Solution**: Break large tasks into smaller chunks

#### Environment Variables Missing
- **Check**: Variables set in Netlify dashboard
- **Check**: Variables available at runtime (not just build time)

### Debug Steps
1. **Check Function Logs**: Look for execution history
2. **Test Manually**: Call function via URL to test logic
3. **Verify Schedule**: Ensure cron syntax is correct
4. **Check Dependencies**: Ensure all imports are available

## 🔄 Manual Triggering

You can manually trigger scheduled functions for testing:

### Via API Call
```bash
curl -X POST https://your-site.netlify.app/.netlify/functions/scheduled-bucket-watcher
```

### Via Netlify Dashboard
1. Go to Functions tab
2. Click on function name
3. Use "Trigger function" button (if available)

## 📝 Best Practices

### 1. **Error Handling**
```python
try:
    # Function logic
    result = process_files()
    return success_response(result)
except Exception as e:
    print(f"Error: {e}")
    return error_response(str(e))
```

### 2. **Timeout Management**
- Keep functions under 30 seconds for reliability
- Use async processing for long tasks
- Implement checkpointing for resumable operations

### 3. **Logging**
```python
print(f"🔄 Starting scheduled task at {datetime.now()}")
print(f"✅ Processed {count} items successfully")
print(f"❌ Failed to process {filename}: {error}")
```

### 4. **Resource Management**
- Close database connections
- Clean up temporary files
- Limit memory usage

## 🎯 Function Limits

- **Execution Time**: 30 seconds max (configurable)
- **Memory**: 1024 MB max
- **Frequency**: Maximum once per minute
- **Concurrent Executions**: Limited by Netlify plan

## 📈 Scaling Considerations

For high-volume processing:
1. **Batch Processing**: Process multiple files per execution
2. **Queue Systems**: Use external queue for large workloads
3. **Database Optimization**: Efficient queries and connections
4. **Error Recovery**: Implement retry logic and dead letter queues 