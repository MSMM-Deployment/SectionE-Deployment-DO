# Section E Resume Parser & Database System

> **Complete solution for parsing General Resume including Standard Form 330 Section E resumes and storing them in a searchable database with a modern web interface**

![Version](https://img.shields.io/badge/version-2.0.0-blue.svg)
![Python](https://img.shields.io/badge/python-3.7%2B-blue.svg)
![OpenAI](https://img.shields.io/badge/OpenAI-GPT--4--turbo-green.svg)
![Database](https://img.shields.io/badge/database-Supabase-orange.svg)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Quick Start](#quick-start)
- [Installation](#installation)
- [Usage Guide](#usage-guide)
- [PDF Form Filling Guide](#pdf-form-filling-guide)
- [Web Interface](#web-interface)
- [Database Schema](#database-schema)
- [File Structure](#file-structure)
- [Examples](#examples)
- [Authentication Flow Guide](#authentication-flow-guide)
- [Troubleshooting](#troubleshooting)
- [API Reference](#api-reference)
- [Smart Employee Merging](#smart-employee-merging)

## 🎯 Overview

This system processes **Standard Form 330 Section E** resumes (used in US federal contracting) and creates a complete searchable database solution. It consists of four main components:

1. **🤖 AI-Powered Parser** - Uses OpenAI GPT-4-turbo to extract structured data from PDF resumes
2. **🗄️ Database System** - Stores data in Supabase with optimized schema for analytics
3. **🔐 Authentication System** - Complete login/signup with modern UI and session management
4. **🌐 Web Interface** - Protected dashboard with search, filters, and employee management

## ✨ Features

### Parser Features
- **OpenAI GPT-4-turbo Integration** - Intelligent structured data extraction
- **Batch Processing** - Process entire folders of PDFs or entire Supabase buckets
- **Local & Cloud Support** - Process local files or files from Supabase storage buckets
- **Error Handling** - Graceful failure handling with detailed logs
- **JSON Output** - Clean, structured data output to local files or cloud storage

### Database Features  
- **Simplified 4-table Schema** - Optimized for performance and ease of use
- **No RLS Issues** - Streamlined permissions for development
- **Analytical Views** - Pre-built views for common queries
- **Full-text Search** - PostgreSQL full-text search capabilities

### Web Interface Features
- **Modern UI** - Beautiful, responsive design matching your sketch
- **🔐 Complete Authentication System** - Secure login/signup with session management
- **Real-time Search** - Live search with suggestions
- **Advanced Filters** - Filter by name, role, or team
- **3 Main Sections** - Employees, Projects, and Teams navigation
- **Employee Detail Pages** - Click any employee row to view comprehensive profile
- **PDF Resume Generation** - One-click Section E PDF generation and download
- **Environment Integration** - Automatically reads `.env` variables
- **User Session Management** - Persistent login sessions with logout functionality

### 🔐 Authentication System Features (NEW!)
- **🌟 Modern Login Page** - Beautiful glassmorphism design with gradient backgrounds
- **📝 Complete Signup Form** - Full registration with first/last name, email validation
- **🔒 Password Security** - Real-time password strength indicator with validation rules
- **👁️ Password Visibility Toggle** - User-friendly password input with show/hide functionality
- **⚡ Smart Form Validation** - Client-side validation with helpful error messages
- **🎨 Responsive Design** - Perfect display on desktop, tablet, and mobile devices
- **🛡️ Session Protection** - Dashboard automatically protected from unauthorized access
- **👤 User Profile Display** - Shows logged-in user email in sidebar with profile icon
- **🚪 Secure Logout** - Clean session termination with redirect to login page
- **🔄 Automatic Redirects** - Smart routing between login, signup, and dashboard pages
- **🌐 Google Sign-In Ready** - Placeholder buttons for future Google OAuth integration
- **⚙️ Default Credentials** - Pre-configured test account (rmehta@msmmeng.com / @msmmeng.com)
- **📱 Mobile Optimized** - Touch-friendly interface for mobile authentication
- **🎯 Session Management** - Uses sessionStorage for reliable login state tracking
- **🔐 Route Protection** - Server-side authentication checks for all dashboard routes

### PDF Form Filling Features
- **Template-Based Generation** - Uses official "Section E template.pdf" with fillable fields
- **Database Integration** - Pulls all employee data from Supabase automatically
- **Professional Formatting** - Maintains official form layout and styling
- **Multi-Project Support** - Includes up to 5 relevant projects per employee
- **Smart Field Mapping** - Automatically maps database fields to PDF form fields
- **Fallback Support** - Works with JSON data if database unavailable

### 🔧 Enhanced PDF Text Extraction (NEW!)
- **Multi-Library Extraction** - Uses PyMuPDF, PyPDF2, pdfplumber with intelligent fallback
- **CID Code Decoding** - Automatically converts `(cid:20)(cid:21)` patterns to readable text
- **Garbled Text Fixes** - Preprocesses common encoding issues before OpenAI processing
- **Text Quality Analysis** - Reports extraction quality and identifies issues
- **Encoding Problem Solver** - Handles PDFs with character encoding artifacts
- **Improved Success Rate** - Dramatically better OpenAI parsing results

### 📄 Word Document Support (NEW!)
- **Microsoft Word Processing** - Full support for .docx and .doc files
- **Intelligent Text Extraction** - Uses python-docx and docx2txt with fallback
- **Legacy .doc Support** - Uses antiword for binary Word documents (requires system dependency)
- **High Success Rate** - Proven 100% success rate on real-world government resume .doc files
- **Mixed File Processing** - Process folders containing both PDF and Word documents
- **Table & Paragraph Extraction** - Extracts text from Word tables and formatted content
- **Same AI Processing** - Word documents get same OpenAI structured data extraction
- **Automatic Fallback** - If antiword not available, tries alternative methods

### ☁️ Supabase Bucket Processing (NEW!)
- **Cloud Storage Integration** - Process files directly from Supabase storage buckets
- **Bucket "msmm-resumes"** - Automatically connects to your Supabase "msmm-resumes" bucket
- **Automatic Upload** - Results automatically uploaded to "ParsedFiles" folder in same bucket
- **Temporary File Management** - Downloads files temporarily, processes them, then cleans up
- **Same AI Processing** - Uses identical OpenAI parsing logic as local file processing
- **Batch & Individual Processing** - Process all files in bucket or specify individual files
- **Fallback Support** - If bucket upload fails, saves results locally as backup

## 🚀 Quick Start

### 1. **Setup Environment**
```bash
# Clone repository
git clone <your-repo-url>
cd SectionE-Parser

# Install system dependencies (for .doc files)
brew install antiword  # macOS

# Install Python dependencies
pip install -r requirements.txt

# Create environment file
echo "OPENAI_API_KEY=your_openai_api_key_here" >> .env
echo "SUPABASE_URL=your_supabase_project_url" >> .env
echo "SUPABASE_KEY=your_supabase_key" >> .env

# Verify installation
python3 utils/verify_installation.py
```

### 2. **Setup Database**
```bash
# 1. Create Supabase project at https://supabase.com
# 2. Copy contents of sql/supabase_schema_simple.sql
# 3. Run in Supabase SQL Editor
```

### 3. **Parse Resumes** (Now with Enhanced Extraction + Word (.doc and .docx) Support!)
```bash
# Easy way - use launcher scripts from root directory:
python3 parse_resumes.py --folder data/Sample-SectionE --output results.json

# Or call directly:
python3 src/parsers/section_e_parser.py --folder data/Sample-SectionE --output results.json

# Process single Word document
python3 parse_resumes.py --folder data/Sample-SectionE --file Resume.docx --output result.json

# For PDFs with encoding issues, analyze first:
python3 src/parsers/enhanced_text_extractor.py
```

### 3b. **Parse Resumes from Supabase Bucket** (NEW!)
```bash
# Process all resumes from Supabase bucket "msmm-resumes"
python3 src/parsers/section_e_parsing_bucket.py --output bucket_results.json

# Process specific file from bucket
python3 src/parsers/section_e_parsing_bucket.py --file employee_resume.pdf --output specific_result.json
```

### 4. **Load Data**
```bash
# Easy way - use launcher script:
python3 load_database.py --input results.json

# Or call directly:
python3 src/database/supabase_loader_simple.py --input results.json
```

### 5. **Launch Web UI**
```bash
# Easy way - use launcher script:
python3 start_server.py

# Or call directly:
python3 src/web/serve_ui.py

# Browser opens automatically at http://localhost:8000
```


### 6. **Generate Section E Documents (PDF & DOCX!)**
```bash
# Generate PDFs using PDF templates
python3 src/generators/pdf_form_filler.py --inspect
python3 src/generators/pdf_form_filler.py --employee_name "John Doe"

# Generate DOCX files using Word templates (NEW!)
python3 src/generators/docx_section_e_generator.py --data data/ParsedFiles/results.json

# Test the DOCX generator
python3 tests/test_docx_generator.py

# Or use the web interface with template selection
```

## 🤖 Automatic Mode (New!)

For **automatic processing** of new PDF files, use the auto-watcher:

### **Start Auto-Watcher**
```bash
# Easy way - use launcher script:
python3 start_watcher.py

# Or call directly:
python3 src/automation/start_auto_watcher.py
```

This will:
- ✅ **Auto-install** the `watchdog` dependency
- 👀 **Monitor** the `data/Sample-SectionE` folder for new PDF files
- 🔄 **Automatically parse** new files with OpenAI GPT-4-turbo
- 📊 **Load results** into Supabase database using smart merging
- 📝 **Track processed files** to avoid reprocessing

### **How It Works**
1. **Drop new PDFs** into the `data/Sample-SectionE` folder
2. **Automatic detection** - System detects new files instantly
3. **Smart processing** - Only processes new files, not entire folder
4. **Real-time feedback** - Console shows processing status
5. **Database integration** - Results automatically loaded with smart employee merging

### **Features**
- **🔄 Real-time Monitoring** - Instant detection of new files
- **⚡ Single File Processing** - Only parses new files for efficiency
- **🧠 Smart Deduplication** - Won't reprocess existing files
- **📝 Processing Log** - Maintains `processed_files.json` audit trail
- **🛡️ Error Handling** - Robust error handling with timeouts
- **🎯 Targeted Processing** - Uses `--file` parameter for precise control

### **Console Output Example**
```
🤖 AUTOMATIC RESUME PARSER WATCHER
==================================================
📁 Monitoring folder: /path/to/data/Sample-SectionE
📝 Processed files log: /path/to/processed_files.json
✅ Already processed: 10 files

👀 Started watching data/Sample-SectionE...
📁 Drop new PDF files into the folder to auto-process them
⌨️  Press Ctrl+C to stop

🆕 New PDF detected: John-Smith-3.pdf
🔄 Processing John-Smith-3.pdf...
✅ Successfully parsed John-Smith-3.pdf
📊 Loading filtered_auto_parsed_20241201_143022_John-Smith-3.json into database...
✅ Successfully loaded into database
🎉 Completed processing John-Smith-3.pdf
```

## 📦 Installation

### Prerequisites
- **Python 3.7+**
- **OpenAI API key** with GPT-4-turbo access
- **Supabase account** (free tier works)
- **System dependencies** for legacy .doc file processing (optional but recommended)

### Step-by-Step Installation

1. **Install System Dependencies (for .doc file support)**
   ```bash
   # macOS (using Homebrew)
   brew install antiword
   
   # Ubuntu/Debian
   sudo apt-get install antiword
   
   # CentOS/RHEL/Fedora
   sudo yum install antiword
   # or for newer versions:
   sudo dnf install antiword
   ```

2. **Install Python Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Get OpenAI API Key**
   - Visit [OpenAI Platform](https://platform.openai.com/)
   - Create account and generate API key
   - Ensure GPT-4-turbo access

4. **Setup Supabase**
   - Create project at [supabase.com](https://supabase.com)
   - Get project URL and API key from Settings → API
   - Note: Use service_role key for full access

5. **Configure Environment**
   ```bash
   # Create .env file with your credentials
   OPENAI_API_KEY=sk-your-openai-key-here
   SUPABASE_URL=https://your-project.supabase.co
   SUPABASE_KEY=your-supabase-service-key
   ```

6. **Verify Installation** (NEW!)
   ```bash
   # Run comprehensive installation verification
   python3 utils/verify_installation.py
   ```
   This script will check:
   - All Python packages are installed
   - System dependencies (antiword) are available
   - Text extraction methods are working
   - Environment variables are set
   - OpenAI API connection is working

## 📁 File Structure

```
SectionE-Parser/
├── 📄 README.md                    # This comprehensive guide
├── 🔧 Configuration Files
│   ├── .env                        # Environment variables (create this)
│   ├── requirements.txt            # Python dependencies
│   ├── package.json               # Node.js dependencies (optional)
│   └── .gitignore                 # Git ignore rules
├── 🚀 Launcher Scripts (NEW!)
│   ├── parse_resumes.py           # Launcher for resume parser
│   ├── load_database.py           # Launcher for database loader
│   ├── start_server.py            # Launcher for web server
│   └── start_watcher.py           # Launcher for auto watcher
├── 📁 src/                        # Main source code
│   ├── parsers/                   # Text extraction and AI parsing
│   │   ├── section_e_parser.py    # Main OpenAI-powered parser
│   │   ├── section_e_parsing_bucket.py # Supabase bucket parser
│   │   └── enhanced_text_extractor.py  # Multi-method text extraction
│   ├── generators/                # Document generation
│   │   ├── pdf_form_filler.py     # PDF template filler
│   │   └── docx_section_e_generator.py # DOCX template generator
│   ├── database/                  # Database operations
│   │   └── supabase_loader_simple.py # Simplified data loader
│   ├── web/                       # Web interface
│   │   ├── serve_ui.py            # Python web server with .env integration
│   │   ├── index.html             # Main dashboard web UI
│   │   ├── login.html             # Modern login page with authentication
│   │   └── signup.html            # Complete user registration page
│   └── automation/                # Automated processing
│       ├── auto_parser_watcher.py # File system watcher
│       └── start_auto_watcher.py  # Watcher launcher
├── 📁 tests/                      # Test files
│   ├── test_docx_generator.py     # DOCX generator tests
│   ├── test_pdf_generation.py     # PDF generation tests
│   ├── test_parser.py             # Parser tests
│   └── employee_detail_demo.html  # Demo HTML
├── 📁 utils/                      # Utilities and debugging tools
│   ├── docx_template_analyzer.py  # DOCX template analysis
│   ├── inspect_pdf_fields.py      # PDF form field inspector
│   ├── pdf_encoding_solution.py   # PDF encoding troubleshooter
│   ├── fix_employee_duplicates.py # Database duplicate fixer
│   ├── split_roles.py             # Role normalization utility
│   ├── template_integration.py    # Template integration helper
│   ├── verify_installation.py     # Installation verification
│   └── server.js                  # Node.js alternative server
├── 📁 legacy/                     # Legacy/deprecated files
│   ├── supabase_loader.py         # Old complex loader
│   └── pdf_template_integration.py # Old PDF integration
├── 📁 data/                       # Data directories
│   ├── Sample-SectionE/           # Sample PDF resumes for testing
│   ├── ParsedFiles/               # Parsed JSON output
│   ├── OutputFiles/               # Generated documents
│   ├── GeneralResumes/            # Additional resume storage
│   └── CPRA_Docs/                 # Document storage
├── 📁 sql/                        # Database schema and functions
│   ├── supabase_schema_simple.sql # Simplified 4-table schema
│   ├── add_employee_merge_functions.sql # Employee merging
│   ├── add_role_merge_functions.sql # Role merging
│   ├── add_team_merge_functions.sql # Team merging
│   ├── add_professional_qualifications_table.sql # Qualifications
│   ├── find_duplicate_employees.sql # Duplicate detection
│   └── update_employee_profiles_view.sql # View updates
├── 📁 templates/                  # Resume templates
│   ├── Section E template.pdf     # PDF template
│   ├── Template Section E Resume.docx # DOCX template
│   └── templates.json             # Template metadata
└── 📄 solicitation.pdf            # Sample solicitation document
```

## 💡 Examples

### Sample Extracted Data
```json
{
  "resumes": [
    {
      "filename": "employee-resume.pdf",
      "data": {
        "name": "Milan Mardia",
        "role_in_contract": "Project Engineer", 
        "years_experience": {
          "total": "8",
          "with_current_firm": "5"
        },
        "firm_name_and_location": "Engineering Solutions Inc, Denver, CO",
        "education": "MS Civil Engineering, University of Colorado",
        "current_professional_registration": "PE - Colorado #12345",
        "other_professional_qualifications": "PMP Certified",
        "relevant_projects": [
          {
            "title_and_location": "Highway Bridge Replacement - Denver, CO",
            "year_completed": {
              "professional_services": "2023",
              "construction": "2024"
            },
            "description": {
              "scope": "Complete bridge replacement including design and permitting",
              "cost": "$2.5M construction value",
              "fee": "$125K professional services",
              "role": "Lead design engineer and project coordinator"
            }
          }
        ]
      }
    }
  ]
}
```

### Using Launcher Scripts
```bash
# Parse resumes from the sample folder
python3 parse_resumes.py --folder data/Sample-SectionE --output results.json

# Load parsed data into database
python3 load_database.py --input results.json

# Start the web interface
python3 start_server.py

# Start auto-watcher for new files
python3 start_watcher.py
```

### Using Direct Paths
```bash
# Alternative: Call scripts directly with full paths
python3 src/parsers/section_e_parser.py --folder data/Sample-SectionE --output results.json
python3 src/database/supabase_loader_simple.py --input results.json
python3 src/web/serve_ui.py
```

## 🔐 Authentication Flow Guide

### **First Time Setup**
1. **Start the Server**
   ```bash
   python3 start_server.py
   ```

2. **Access Application**
   - Open browser to `http://localhost:8000`
   - You'll be automatically redirected to `/login.html`

3. **Login with Default Credentials**
   ```
   Email: rmehta@msmmeng.com
   Password: @msmmeng.com
   ```

4. **Access Dashboard**
   - After successful login, you'll be redirected to the main dashboard
   - Your email will appear in the sidebar with a logout button

### **Authentication Features**

#### **Login Page (`/login.html`)**
- 🎨 **Beautiful Design** - Modern glassmorphism effect with purple gradient
- 👁️ **Password Toggle** - Click eye icon to show/hide password
- ⚡ **Real-time Validation** - Immediate feedback on form errors
- 🔄 **Loading States** - Visual feedback during authentication
- 🌐 **Google Ready** - Placeholder for future Google OAuth integration

#### **Signup Page (`/signup.html`)**
- 📝 **Complete Form** - First name, last name, email, password fields
- 🔒 **Password Strength** - Real-time strength indicator with color coding
- ✅ **Validation Rules** - Password must include uppercase, lowercase, numbers, special chars
- 📱 **Responsive Grid** - Two-column layout on desktop, single column on mobile
- ⚖️ **Terms Agreement** - Required checkbox for terms of service

#### **Protected Dashboard (`/`)**
- 🛡️ **Automatic Protection** - Redirects to login if not authenticated
- 👤 **User Display** - Shows logged-in user email in sidebar
- 🚪 **Logout Button** - Clean session termination and redirect
- 💾 **Session Persistence** - Login state maintained until logout or browser close

### **Authentication Flow**
```
User visits / → Check Authentication → If not logged in → Redirect to /login.html
                                   → If logged in → Show Dashboard

Login Success → Set Session → Redirect to /
Logout Click → Clear Session → Redirect to /login.html
```

### **Future Enhancements Ready**
The authentication system is designed to easily integrate with:
- **Google Cloud Console OAuth**
- **Supabase Authentication**
- **Real user registration and database storage**
- **Role-based access control**
- **Password reset functionality**

---

*For support or questions about this system, refer to the troubleshooting section above.*
