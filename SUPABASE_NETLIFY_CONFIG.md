# Supabase Configuration for Netlify Deployment

## 🔧 **Environment Variables Setup**

Your application requires Supabase credentials to function properly. Follow these steps to configure them in Netlify:

## 📋 **Required Environment Variables**

You need to set these 2 environment variables in your Netlify dashboard:

### **1. SUPABASE_URL**
- **Variable Name**: `SUPABASE_URL`
- **Value**: `https://clcufcjifbvpbtsczkmx.supabase.co`
- **Description**: Your Supabase project URL

### **2. SUPABASE_KEY**
- **Variable Name**: `SUPABASE_KEY`  
- **Value**: `eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNsY3VmY2ppZmJ2cGJ0c2N6a214Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTMxODQyNSwiZXhwIjoyMDY2ODk0NDI1fQ.fQTie6YIgPMl_8bo2W6e6jCjk7tGxWFXdSZZj0RTNa0`
- **Description**: Your Supabase service role key (for backend functions)

## 🚀 **How to Add Environment Variables in Netlify**

### **Step 1: Access Your Site Settings**
1. Go to your [Netlify Dashboard](https://app.netlify.com)
2. Click on your deployed site
3. Navigate to **Site settings**

### **Step 2: Add Environment Variables**
1. In the sidebar, click **Environment variables**
2. Click **Add a variable**
3. Add each variable:

**First Variable:**
```
Name: SUPABASE_URL
Value: https://clcufcjifbvpbtsczkmx.supabase.co
Scopes: [Select all: Builds, Functions, Deploy previews, Branch deploys]
```

**Second Variable:**
```
Name: SUPABASE_KEY
Value: eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImNsY3VmY2ppZmJ2cGJ0c2N6a214Iiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc1MTMxODQyNSwiZXhwIjoyMDY2ODk0NDI1fQ.fQTie6YIgPMl_8bo2W6e6jCjk7tGxWFXdSZZj0RTNa0
Scopes: [Select all: Builds, Functions, Deploy previews, Branch deploys]
```

### **Step 3: Deploy**
1. Click **Save**
2. **Trigger a new deploy** (this is important - environment variables only take effect on new deploys)
3. Go to **Deploys** tab and click **Trigger deploy → Deploy site**

## ✅ **Verification**

After deploying with the environment variables:

### **1. Check Configuration API**
Visit: `https://your-site.netlify.app/api/config`

Should return:
```json
{
  "status": "success",
  "supabaseConfigured": true,
  "hasUrl": true,
  "hasKey": true
}
```

### **2. Check Main Application**
Visit: `https://your-site.netlify.app`

- **✅ Success**: You should see the employee dashboard with data
- **❌ Still in demo mode**: Environment variables not properly set

## 🔧 **How the System Works**

### **Frontend (Browser)**
- JavaScript in `index.html` connects to Supabase using these credentials
- Environment variables are injected during the build process
- Template placeholders `{{SUPABASE_URL}}` and `{{SUPABASE_KEY}}` are replaced with actual values

### **Backend (Serverless Functions)**
- All API endpoints in `netlify/functions/` use these environment variables
- Functions access credentials via `os.getenv('SUPABASE_URL')` and `os.getenv('SUPABASE_KEY')`
- Automatic resume processing and database operations require these credentials

### **Build Process**
1. Netlify reads environment variables during build
2. `build.py` copies HTML files to `dist/` directory
3. `serve_ui.py` logic injects environment variables into HTML templates
4. Final HTML served to users has actual Supabase credentials

## 🛠️ **Troubleshooting**

### **Problem**: Still seeing "Configuration Required" message
**Solution**: 
1. Verify environment variables are set exactly as shown above
2. Make sure you triggered a new deploy after adding them
3. Check that scopes include "Builds" and "Functions"

### **Problem**: Functions returning "Supabase not configured" error
**Solution**:
1. Check that `SUPABASE_KEY` scope includes "Functions"
2. Verify the key is the service role key (not anon key)
3. Trigger a new deploy

### **Problem**: Frontend shows demo mode but functions work
**Solution**:
1. Check that `SUPABASE_URL` and `SUPABASE_KEY` scopes include "Builds"
2. The frontend injection happens during build time
3. Trigger a new deploy

## 📝 **Environment Variable Scopes**

| Scope | Purpose | Required For |
|-------|---------|--------------|
| **Builds** | Available during build process | Frontend credential injection |
| **Functions** | Available in serverless functions | Backend API endpoints |
| **Deploy previews** | Available in PR previews | Testing changes |
| **Branch deploys** | Available in branch deploys | Development branches |

## 🔒 **Security Notes**

- The service role key is used for backend functions (has elevated permissions)
- The same key is injected into frontend (becomes public)
- This is acceptable for this application architecture
- In production, consider using Row Level Security (RLS) policies in Supabase

## 📊 **Expected Functionality After Setup**

Once properly configured, your application will have:

✅ **Employee Database**: Browse and search employee profiles  
✅ **Project Management**: View and manage project data  
✅ **PDF Generation**: Create custom resumes and reports  
✅ **Template Management**: Upload and use document templates  
✅ **Automatic Processing**: Background resume processing from Supabase bucket  
✅ **Data Analytics**: Team and role analytics  

## 🚨 **Important Notes**

1. **Always trigger a new deploy** after adding environment variables
2. **Include all scopes** (Builds, Functions, Deploy previews, Branch deploys)
3. **Use the exact variable names**: `SUPABASE_URL` and `SUPABASE_KEY`
4. **Copy the values exactly** (no extra spaces or characters)

## 📞 **Need Help?**

If you continue having issues:
1. Check the [Netlify Environment Variables Documentation](https://docs.netlify.com/environment-variables/overview/)
2. Verify your Supabase project is active and accessible
3. Check function logs in Netlify dashboard for specific error messages 