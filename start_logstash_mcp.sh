#!/bin/bash

echo "🚀 Starting Logstash MCP Server"
echo "==============================="

# Check if Python dependencies are installed
echo "📦 Checking dependencies..."
python3 -c "import mcp, aiohttp" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "❌ Missing dependencies. Installing..."
    pip3 install -r requirements.txt
fi

# Set default environment variables if not set
export LOGSTASH_API_BASE="${LOGSTASH_API_BASE:-http://localhost:9600}"

echo "🔧 Configuration:"
echo "   API Base: $LOGSTASH_API_BASE"
echo ""

# Test connectivity to Logstash (optional)
echo "🔍 Testing Logstash connectivity..."
curl -s "$LOGSTASH_API_BASE/_node" >/dev/null 2>&1
if [ $? -eq 0 ]; then
    echo "✅ Logstash is reachable"
else
    echo "⚠️  Warning: Cannot reach Logstash at $LOGSTASH_API_BASE"
    echo "   The MCP server will still start, but tools may fail until Logstash is available"
fi

echo ""
echo "🎯 Starting MCP Server..."
echo "   The server will display usage instructions on startup"
echo "   Press Ctrl+C to stop"
echo "   Server will communicate via stdin/stdout for MCP protocol"
echo ""

# Start the MCP server
python3 logstash_mcp_server.py
