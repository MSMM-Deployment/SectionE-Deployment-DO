/**
 * Section E Resume Database Server (Node.js version)
 * 
 * Alternative Express.js server for the Section E resume system.
 * This provides the same functionality as serve_ui.py but using Node.js.
 * 
 * Features:
 * - Serves the HTML UI with environment variable injection
 * - Provides API endpoints for configuration and health checks
 * - Handles CORS for development
 * - Graceful shutdown handling
 * 
 * Usage: node server.js
 * Alternative to: python serve_ui.py
 */

const express = require('express');
const path = require('path');
const fs = require('fs');
require('dotenv').config(); // Load environment variables from .env file

const app = express();
const PORT = process.env.PORT || 3000;

// Enable CORS for development
// This allows the frontend to make API calls during development
app.use((req, res, next) => {
    res.header('Access-Control-Allow-Origin', '*');
    res.header('Access-Control-Allow-Headers', 'Origin, X-Requested-With, Content-Type, Accept');
    next();
});

// Serve static files (CSS, JS, images, etc.)
// Excludes index.html from auto-serving so we can inject environment variables
app.use(express.static('.', {
    index: false  // Don't auto-serve index.html - we'll handle it manually
}));

// Main route - serve index.html with environment variables injected
// This mirrors the functionality of serve_ui.py but in Node.js
app.get('/', (req, res) => {
    try {
        // Read the HTML template file from disk
        let htmlContent = fs.readFileSync(path.join(__dirname, 'index.html'), 'utf8');
        
        // Get environment variables from .env file (loaded by dotenv)
        // Use placeholder values if credentials are not found
        const supabaseUrl = process.env.SUPABASE_URL || 'YOUR_SUPABASE_URL_HERE';
        const supabaseKey = process.env.SUPABASE_KEY || 'YOUR_SUPABASE_ANON_KEY_HERE';
        
        // Replace placeholder JavaScript constants with actual values
        // This allows the frontend to connect to Supabase without exposing credentials in source
        htmlContent = htmlContent.replace(
            "const SUPABASE_URL = 'YOUR_SUPABASE_URL_HERE';",
            `const SUPABASE_URL = '${supabaseUrl}';`
        );
        
        htmlContent = htmlContent.replace(
            "const SUPABASE_ANON_KEY = 'YOUR_SUPABASE_ANON_KEY_HERE';",
            `const SUPABASE_ANON_KEY = '${supabaseKey}';`
        );
        
        // Update the configuration message to show actual values
        htmlContent = htmlContent.replace(
            "SUPABASE_URL = 'your_supabase_project_url'<br>",
            `SUPABASE_URL = '${supabaseUrl}'<br>`
        );
        
        htmlContent = htmlContent.replace(
            "SUPABASE_ANON_KEY = 'your_supabase_anon_key'",
            `SUPABASE_ANON_KEY = '${supabaseKey}'`
        );
        
        // Set content type and send
        res.setHeader('Content-Type', 'text/html');
        res.send(htmlContent);
        
        // Log the status
        if (supabaseUrl !== 'YOUR_SUPABASE_URL_HERE' && supabaseKey !== 'YOUR_SUPABASE_ANON_KEY_HERE') {
            console.log('✅ Environment variables loaded successfully');
            console.log(`📊 Supabase URL: ${supabaseUrl}`);
            console.log(`🔑 Supabase Key: ${supabaseKey.substring(0, 20)}...`);
        } else {
            console.log('⚠️  Environment variables not found - showing demo mode');
        }
        
    } catch (error) {
        console.error('Error serving HTML:', error);
        res.status(500).send('Error loading the application');
    }
});

// API endpoint to get environment variables (optional - for debugging)
app.get('/api/config', (req, res) => {
    res.json({
        supabaseConfigured: !!(process.env.SUPABASE_URL && process.env.SUPABASE_KEY),
        hasUrl: !!process.env.SUPABASE_URL,
        hasKey: !!process.env.SUPABASE_KEY
    });
});

// Health check endpoint
app.get('/health', (req, res) => {
    res.json({ 
        status: 'healthy', 
        timestamp: new Date().toISOString(),
        env: process.env.NODE_ENV || 'development'
    });
});

// Start the server
app.listen(PORT, () => {
    console.log('\n🚀 Section E Resume Database Server');
    console.log('=====================================');
    console.log(`📍 Server running at: http://localhost:${PORT}`);
    console.log(`📁 Serving from: ${__dirname}`);
    
    // Check environment setup
    if (process.env.SUPABASE_URL && process.env.SUPABASE_KEY) {
        console.log('✅ Environment variables detected');
        console.log('🔗 Database connection will be enabled');
    } else {
        console.log('⚠️  No .env file detected - demo mode will be available');
        console.log('💡 Create a .env file with SUPABASE_URL and SUPABASE_KEY to enable database');
    }
    
    console.log('\n🌐 Open your browser and go to: http://localhost:3000');
    console.log('=====================================\n');
});

// Graceful shutdown
process.on('SIGTERM', () => {
    console.log('🛑 Server shutting down gracefully...');
    process.exit(0);
});

process.on('SIGINT', () => {
    console.log('\n🛑 Server shutting down gracefully...');
    process.exit(0);
}); 