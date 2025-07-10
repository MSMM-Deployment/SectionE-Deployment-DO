# Netlify Deployment Guide for Section E Resume Database

## 🎯 Overview

This guide provides step-by-step instructions for deploying the Section E Resume Database application to Netlify. The application has been prepared with:

- **Serverless Functions**: API endpoints converted to Netlify Functions
- **Static File Serving**: HTML, CSS, JS served directly by Netlify
- **Background Processing**: Scheduled functions for automatic resume processing
- **Environment Variables**: Secure configuration through Netlify UI
- **Build Pipeline**: Automated build process with proper asset organization
- **✅ Path Compatibility**: All file paths have been fixed for Netlify serverless environment

> 📝 **Path Fixes Applied**: All path issues have been resolved! See `NETLIFY_PATH_FIXES.md` for detailed changes. The application now works seamlessly in both local development and Netlify serverless environments.

## 📋 Prerequisites

Before starting, ensure you have:

1. ✅ **GitHub Repository**: Your code is pushed to GitHub and connected to Netlify
2. ✅ **Netlify Account**: Access to the Netlify web dashboard
3. ✅ **Supabase Project**: Database and storage bucket set up
4. ✅ **OpenAI API Key**: For AI-powered features (optional)
5. ✅ **Domain Access**: If using custom domain (optional)

## 🚀 Part 1: Initial Netlify Site Setup

### Step 1: Access Your Netlify Dashboard
1. Go to [https://app.netlify.com/](https://app.netlify.com/)
2. Log in with your Netlify account
3. Navigate to your **Sites** dashboard

### Step 2: Locate Your Connected Site
Since you mentioned the GitHub repository is already connected:
1. Find your site in the Sites list (it should show your repository name)
2. Click on the site name to enter the site dashboard
3. Note your site's URL (e.g., `https://amazing-site-name.netlify.app/`)

### Step 3: Access Site Settings
1. In your site dashboard, click **"Site settings"** in the top navigation
2. This takes you to the configuration panel for your deployment

## ⚙️ Part 2: Build & Deploy Configuration

### Step 4: Configure Build Settings
1. In Site Settings, click **"Build & deploy"** in the left sidebar
2. Scroll to **"Build settings"** section
3. Click **"Edit settings"**

Configure the following:

#### Repository Settings:
- **Repository**: Should already show your GitHub repo
- **Branch**: `main` (or your default branch)
- **Base directory**: Leave empty (we deploy from root)

#### Build Settings:
- **Build command**: `pip install -r requirements.txt && python3 build.py`
- **Publish directory**: `dist`
- **Functions directory**: `netlify/functions`

#### Advanced Build Settings:
4. Scroll down to **"Environment variables"** (we'll configure these in the next step)
5. Click **"Save"** to apply build settings

### Step 5: Set Up Environment Variables
This is **CRITICAL** for your application to work properly.

1. In **"Build & deploy"**, scroll to **"Environment variables"**
2. Click **"Edit variables"**
3. Add the following variables one by one:

#### Required Variables:

**SUPABASE_URL**
- **Key**: `SUPABASE_URL`
- **Value**: `https://clcufcjifbvpbtsczkmx.supabase.co`
- **Scopes**: Select "All scopes" or at minimum "Build time" and "Runtime"

**SUPABASE_KEY**
- **Key**: `SUPABASE_KEY`
- **Value**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNsY3VmY2ppZmJ2cGJ0c2N6a214Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTMxODQyNSwiZXhwIjoyMDY2ODk0NDI1fQ.fQTie6YIgPMl_8bo2W6e6jCjk7tGxWFXdSZZj0RTNa0`
- **Scopes**: Select "All scopes" or at minimum "Build time" and "Runtime"

> 📖 **For detailed step-by-step configuration instructions, see**: `SUPABASE_NETLIFY_CONFIG.md`

#### Optional Variables:

**OPENAI_API_KEY** (for AI features)
- **Key**: `OPENAI_API_KEY`
- **Value**: Your OpenAI API key (starts with `sk-`)
- **Scopes**: Select "All scopes"

4. Click **"Save"** after adding each variable

### Step 6: Configure Function Settings
1. Still in **"Build & deploy"**, find **"Functions"** section
2. Click **"Edit settings"**
3. Configure:
   - **Functions directory**: `netlify/functions` (should auto-populate)
   - **Node.js version**: Use default (18.x)
   - **Timeout**: 30 seconds
4. Click **"Save"**

## 🔧 Part 3: Advanced Configuration

### Step 7: Verify Scheduled Functions Setup
Netlify's scheduled functions are built-in and work automatically:

1. The scheduled functions are already configured in your code
2. **No plugin installation needed** - it's built into Netlify
3. After deployment, go to **"Functions"** in your site dashboard
4. You should see the scheduled function marked as **"Scheduled"**:
   - `scheduled-bucket-watcher` (runs every 5 minutes)

### Step 8: Configure Redirects and Headers
The `netlify.toml` file already contains the necessary configuration for:
- API endpoint redirects (`/api/*` → serverless functions)
- CORS headers for cross-origin requests
- Security headers

No manual configuration needed - this is handled automatically.

### Step 9: Verify File Structure
Ensure your repository has the following structure:
```
your-repo/
├── netlify.toml              # ✅ Netlify configuration
├── build.py                  # ✅ Build script
├── requirements.txt          # ✅ Python dependencies
├── netlify/
│   └── functions/            # ✅ Serverless functions
│       ├── health.py
│       ├── config.py
│       ├── employees.py
│       ├── templates.py
│       ├── bucket-watcher.py
│       └── scheduled-bucket-watcher.py
├── src/                      # ✅ Source code
├── data/                     # ✅ Data files
├── templates/                # ✅ Document templates
└── ...other files
```

## 🚀 Part 4: Deployment Process

### Step 10: Trigger Your First Deploy
1. Go back to **"Deploys"** tab in your site dashboard
2. Click **"Trigger deploy"** → **"Deploy site"**
3. Or simply push a commit to your GitHub repository

### Step 11: Monitor the Build Process
1. Watch the deploy log in real-time
2. The build process will:
   - Install Python dependencies from `requirements.txt`
   - Run the `build.py` script to organize static files
   - Deploy serverless functions to `/.netlify/functions/`
   - Set up scheduled functions for bucket monitoring

#### Expected Build Output:
```bash
🚀 Building application for Netlify deployment...
==================================================
✅ Created dist directory
✅ Copied index.html
✅ Copied login.html
✅ Copied signup.html
✅ Copied templates directory
✅ Created empty ParsedFiles directory
✅ Set up trigger_queue directory
✅ Created _redirects file
✅ Created .env.example template
✅ Created package.json
✅ Build completed successfully!
```

### Step 12: Verify Successful Deployment
1. Wait for build to complete (green checkmark)
2. Click **"Open production deploy"** or visit your site URL
3. You should see the login page of your application

## 🧪 Part 5: Testing Your Deployment

### Step 13: Test Core Functionality

#### Test 1: Basic Site Access
1. Visit your Netlify site URL
2. You should be redirected to `/login.html`
3. The page should load without errors

#### Test 2: API Endpoints
Test these URLs by visiting them directly:
- `https://your-site.netlify.app/health` → Should return JSON health status
- `https://your-site.netlify.app/api/config` → Should return Supabase configuration status
- `https://your-site.netlify.app/api/employees` → Should return employee list (may be empty initially)

#### Test 3: Login and Dashboard
1. Try logging in with test credentials
2. Navigate to the main dashboard
3. Check that all UI elements load properly

#### Test 4: File Upload (if Supabase configured)
1. Try uploading a test resume file
2. Check that the file appears in your Supabase bucket
3. Verify that the scheduled function processes it (may take up to 5 minutes)

### Step 14: Check Function Logs
1. In Netlify dashboard, go to **"Functions"** tab
2. Click on individual functions to see their logs
3. Monitor for any errors or successful executions

### Step 15: Monitor Scheduled Functions
1. The bucket watcher function runs every 5 minutes
2. Check **"Functions"** → **"scheduled-bucket-watcher"** for execution logs
3. Verify it's checking for new files and processing them

## 🔧 Part 6: Troubleshooting Common Issues

### Issue 1: Build Failures

**Error**: `pip: command not found`
- **Solution**: Ensure your build command includes `pip install -r requirements.txt`

**Error**: `build.py: file not found`
- **Solution**: Verify `build.py` is in your repository root

**Error**: `Python version compatibility`
- **Solution**: Check that `requirements.txt` uses compatible package versions

### Issue 2: Function Errors

**Error**: `502 Bad Gateway` on API calls
- **Solution**: Check function logs for specific error messages
- Verify environment variables are set correctly
- Ensure all imports are available

**Error**: `Supabase connection failed`
- **Solution**: Verify `SUPABASE_URL` and `SUPABASE_KEY` environment variables
- Test credentials in Supabase dashboard

### Issue 3: Static File Issues

**Error**: `404 Not Found` for static files
- **Solution**: Verify files are in the `dist` directory after build
- Check `_redirects` file configuration

**Error**: `CORS errors` in browser console
- **Solution**: Headers are configured in `netlify.toml` - verify the file is properly formatted

### Issue 4: Scheduled Function Issues

**Error**: Scheduled functions not running
- **Solution**: Verify the `@netlify/plugin-scheduled-functions` plugin is installed
- Check the cron expression in `netlify.toml`

## 🚀 Part 7: Going Live

### Step 16: Custom Domain (Optional)
1. In Site Settings, go to **"Domain management"**
2. Click **"Add custom domain"**
3. Enter your domain name
4. Follow DNS configuration instructions
5. Wait for SSL certificate provisioning

### Step 17: Performance Optimization
1. Go to **"Build & deploy"** → **"Post processing"**
2. Enable:
   - **Asset optimization** (minify CSS, JS)
   - **Image optimization** (if using images)
   - **Bundle optimization**

### Step 18: Security Configuration
1. In **"Site settings"** → **"Access control"**
2. Configure password protection if needed
3. Set up role-based access if required

## 📊 Part 8: Monitoring and Maintenance

### Step 19: Set Up Monitoring
1. **Analytics**: Enable Netlify Analytics in Site Settings
2. **Function Logs**: Regularly check function execution logs
3. **Error Tracking**: Monitor for 4xx/5xx errors in access logs

### Step 20: Regular Maintenance Tasks

#### Weekly:
- Check function execution logs for errors
- Verify scheduled functions are processing files
- Monitor Supabase usage and storage

#### Monthly:
- Review and rotate API keys if needed
- Update dependencies in `requirements.txt`
- Check for Netlify feature updates

#### As Needed:
- Process any failed file uploads manually
- Clean up old processed files to save storage
- Update environment variables for new integrations

## 🎯 Part 9: Advanced Features

### Step 21: Enable Branch Previews
1. In **"Build & deploy"** → **"Deploy contexts"**
2. Configure branch deploys for staging/testing
3. Set different environment variables for different branches

### Step 22: Set Up Webhooks (Optional)
1. Go to **"Build & deploy"** → **"Build hooks"**
2. Create webhook URLs for external services
3. Use for triggering rebuilds from external systems

### Step 23: Configure Forms (If Needed)
1. Enable Netlify Forms in Site Settings
2. Configure form handling for contact forms
3. Set up spam protection

## 📝 Summary Checklist

Before considering your deployment complete, verify:

- [ ] ✅ Site builds successfully without errors
- [ ] ✅ All environment variables are set correctly
- [ ] ✅ Static pages (login, dashboard) load properly
- [ ] ✅ API endpoints return expected responses
- [ ] ✅ Supabase database connection works
- [ ] ✅ File upload functionality works
- [ ] ✅ Scheduled functions run every 5 minutes
- [ ] ✅ Function logs show successful executions
- [ ] ✅ No CORS or security errors in browser console
- [ ] ✅ Custom domain configured (if applicable)
- [ ] ✅ SSL certificate is active and valid

## 🆘 Support Resources

If you encounter issues:

1. **Netlify Docs**: [https://docs.netlify.com/](https://docs.netlify.com/)
2. **Function Logs**: Check individual function execution logs in Netlify dashboard
3. **Build Logs**: Review complete build logs for deployment issues
4. **Supabase Logs**: Check Supabase dashboard for database/storage issues
5. **Browser Console**: Check for JavaScript errors or network issues

## 🎉 Congratulations!

Your Section E Resume Database is now live on Netlify with:
- ✅ Secure, scalable serverless architecture
- ✅ Automatic resume processing every 5 minutes
- ✅ Professional-grade deployment pipeline
- ✅ Enterprise-ready monitoring and logging

Your application is ready for production use! 🚀 