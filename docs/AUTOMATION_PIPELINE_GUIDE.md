# Supabase Bucket Automation Pipeline Guide

## Overview

The Section E Parser now includes a fully automated pipeline that monitors the Supabase bucket `msmm-resumes` for new file uploads and automatically processes them through the complete workflow:

1. **Upload Detection** - Monitors bucket for newly uploaded files
2. **Download & Process** - Downloads new files and runs the parser
3. **Database Loading** - Automatically loads parsed results to Supabase
4. **Duplicate Prevention** - Tracks processed files to avoid reprocessing

## Quick Start

### 1. Start the Automation Watcher

```bash
# Simple startup (recommended)
python3 start_bucket_watcher.py

# Or with custom options
python3 src/automation/supabase_bucket_watcher.py --interval 30
```

### 2. Upload Files via Web Interface

1. Open the web interface: `http://localhost:8000`
2. Click the **"Upload Resumes"** button
3. Select PDF, DOCX, or DOC files
4. Files are automatically uploaded to the `msmm-resumes` bucket
5. The watcher detects and processes them automatically

### 3. Monitor Progress

The watcher will show real-time progress:
```
🪣 Monitoring Supabase bucket: msmm-resumes
📝 Processed files log: data/processed_bucket_files.json
✅ Already processed: 0 files
⏱️  Polling interval: 30 seconds

🆕 Found 2 new file(s): 1704814800_resume1.pdf, 1704814801_resume2.pdf
🔄 Processing 1704814800_resume1.pdf...
📥 Downloaded: 1704814800_resume1.pdf (245,678 bytes)
✅ Successfully parsed 1704814800_resume1.pdf
📊 Loading results to database: data/ParsedFiles/auto_bucket_20240109_143022_1704814800_resume1.json
✅ Successfully loaded to database
🎉 Completed processing 1704814800_resume1.pdf
```

## File Workflow

### Upload Process

1. **Web Upload**: User uploads files via "Upload Resumes" button
2. **Bucket Storage**: Files stored in Supabase bucket with timestamp prefix
3. **Immediate Trigger**: Upload success tries to notify watcher (if running)
4. **Polling Detection**: Watcher detects new files within 30 seconds

### Processing Pipeline

```
📄 New File in Bucket
       ↓
📥 Download to temp_processing/
       ↓
🔄 Run section_e_parser.py
       ↓ 
💾 Save to data/ParsedFiles/auto_bucket_[timestamp]_[filename].json
       ↓
📊 Load to Supabase database via supabase_loader_simple.py
       ↓
✅ Mark as processed in data/processed_bucket_files.json
       ↓
🗑️ Clean up temporary files
```

### Duplicate Prevention

The system tracks processed files in `data/processed_bucket_files.json`:

```json
{
  "processed_files": [
    "1704814800_resume1.pdf",
    "1704814801_resume2.pdf"
  ],
  "last_updated": "2024-01-09T14:30:22.123456",
  "bucket_name": "msmm-resumes"
}
```

## Advanced Usage

### Process Specific File

```bash
# Process a single file immediately
python3 src/automation/supabase_bucket_watcher.py --process-file "filename.pdf"
```

### Process All Existing Files

```bash
# Scan bucket and process any unprocessed files
python3 src/automation/supabase_bucket_watcher.py --scan-existing
```

### Custom Polling Interval

```bash
# Check bucket every 10 seconds (faster response)
python3 src/automation/supabase_bucket_watcher.py --interval 10

# Check bucket every 2 minutes (slower, less resource usage)
python3 src/automation/supabase_bucket_watcher.py --interval 120
```

### Monitor Different Bucket

```bash
# Monitor a different bucket
python3 src/automation/supabase_bucket_watcher.py --bucket "other-bucket-name"
```

## Configuration

### Environment Variables

Ensure your `.env` file contains:

```bash
SUPABASE_URL=your_supabase_project_url
SUPABASE_KEY=your_supabase_anon_key
```

### File Types Supported

- **PDF**: `.pdf`
- **Word Documents**: `.docx`, `.doc`

### File Size Limits

- **Upload Limit**: 10MB per file (enforced by web interface)
- **Processing**: No hard limit (but very large files may timeout)

## File Locations

### Input
- **Bucket**: `msmm-resumes` (Supabase storage)

### Output
- **Parsed Results**: `data/ParsedFiles/auto_bucket_[timestamp]_[filename].json`
- **Processed Log**: `data/processed_bucket_files.json`
- **Temporary Files**: `temp_processing/` (auto-cleaned)

### Database
- **Tables**: All standard Supabase tables via `supabase_loader_simple.py`

## Integration with Web Interface

### Upload Button Enhancement

The web interface now includes automation features:

1. **Smart Upload Messages**: Shows automation status after upload
2. **Immediate Triggers**: Attempts to notify running watcher
3. **Fallback Instructions**: Provides manual processing commands if automation isn't running

### Status Checking

```javascript
// The web interface tries to trigger immediate processing
tryTriggerImmediateProcessing(uploadedFiles);
```

### Error Handling

- Upload failures are handled gracefully
- Processing errors are logged but don't stop the watcher
- Network issues trigger automatic retries

## Monitoring & Troubleshooting

### Check Watcher Status

```bash
# See if watcher is running
ps aux | grep supabase_bucket_watcher
```

### View Processed Files Log

```bash
cat data/processed_bucket_files.json
```

### Check Recent Parse Results

```bash
ls -la data/ParsedFiles/auto_bucket_*
```

### Common Issues

#### 1. Watcher Not Detecting Files

- **Cause**: Polling too slow or watcher not running
- **Solution**: Reduce `--interval` or restart watcher

#### 2. Files Not Processing

- **Cause**: Parser errors or missing dependencies
- **Solution**: Check watcher output for error messages

#### 3. Database Loading Fails

- **Cause**: Supabase connection issues or malformed data
- **Solution**: Verify `.env` file and check parser output

#### 4. Duplicate Processing

- **Cause**: Processed files log corrupted
- **Solution**: Check `data/processed_bucket_files.json` format

### Logs and Debugging

The watcher provides extensive logging:

```
📝 Status: 5 processed, 1 processing
🔄 Processing filename.pdf...
📥 Downloaded: filename.pdf (123,456 bytes)
✅ Successfully parsed filename.pdf
📊 Loading results to database: data/ParsedFiles/auto_bucket_20240109_143022_filename.json
✅ Successfully loaded to database
🎉 Completed processing filename.pdf
🗑️ Cleaned up temp file: filename.pdf
```

## Performance Considerations

### Resource Usage

- **CPU**: Moderate during parsing, low during monitoring
- **Memory**: ~100MB base + file size during processing
- **Storage**: Temporary files cleaned automatically
- **Network**: Downloads only new files

### Scalability

- **Concurrent Processing**: Multiple files processed in parallel threads
- **Polling Efficiency**: Only checks for new files, doesn't re-scan processed ones
- **Memory Management**: Files streamed and cleaned up immediately

### Optimization Tips

1. **Faster Detection**: Use shorter polling intervals (10-15 seconds)
2. **Resource Saving**: Use longer intervals (60+ seconds) for low-traffic scenarios
3. **Batch Processing**: Upload multiple files at once for efficiency

## Security

### Access Control

- Uses Supabase RLS (Row Level Security) policies
- Requires valid Supabase credentials in `.env`
- No public file access outside of authenticated users

### File Validation

- File type checking (PDF, DOCX, DOC only)
- File size limits enforced
- Malicious file detection via parser errors

### Data Privacy

- Temporary files deleted after processing
- Parsed data follows existing database security model
- No data stored outside of configured Supabase instance

## Automation Benefits

### For Users

1. **Zero Manual Steps**: Upload → Automatic Processing → Database Ready
2. **Real-time Processing**: Files processed within seconds of upload
3. **Error Recovery**: Failed files can be re-uploaded and processed
4. **Progress Visibility**: Clear status updates throughout process

### For Administrators

1. **Hands-off Operation**: No manual parser runs needed
2. **Scalable**: Handles any number of uploaded files
3. **Reliable**: Duplicate prevention and error handling
4. **Auditable**: Complete logging of all operations

## Migration from Manual Process

### Before Automation

```bash
# Manual 3-step process
python3 src/parsers/section_e_parsing_bucket.py --output results.json
python3 src/database/supabase_loader_simple.py --input results.json
# Manual refresh of web interface
```

### After Automation

```bash
# One-time setup
python3 start_bucket_watcher.py

# Then just upload files via web interface!
```

### Transition Steps

1. **Start the watcher**: `python3 start_bucket_watcher.py`
2. **Process existing files**: Use `--scan-existing` flag
3. **Switch to upload workflow**: Use web interface instead of manual file placement
4. **Monitor automation**: Check logs for successful processing

## Future Enhancements

### Planned Features

- **Webhook Integration**: Real-time triggers instead of polling
- **Processing Queue UI**: Web interface showing processing status
- **Batch Upload**: Multiple file upload with progress tracking
- **Email Notifications**: Alerts for processing completion/errors

### Integration Possibilities

- **Slack/Teams Notifications**: Processing status updates
- **File Preview**: Show parsing progress in web interface
- **Advanced Filtering**: Process only specific file types or patterns
- **Custom Processing Rules**: Different parser settings per file type 