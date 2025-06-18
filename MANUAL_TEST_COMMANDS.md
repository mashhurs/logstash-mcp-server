# Manual MCP Server Testing

## 🚀 Step-by-Step Testing Instructions

### 1️⃣ Start the Server
```bash
python3 logstash_mcp_server.py
```

### 2️⃣ Send Commands in This Exact Order

**IMPORTANT**: Each command must be sent as a single line. Copy and paste each line one at a time.

#### Initialize (REQUIRED FIRST):
```json
{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {"roots": {"listChanged": false}}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}
```

#### List Available Tools (11 total):
```json
{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}
```

#### 1. Check Connectivity (RECOMMENDED FIRST):
```json
{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "logstash_check_connectivity", "arguments": {}}}
```

#### 2. Get Node Information:
```json
{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "logstash_node_info", "arguments": {}}}
```

#### 3. Health Check (Comprehensive Analysis):
```json
{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "logstash_health_check", "arguments": {}}}
```

#### 4. Get Node Statistics:
```json
{"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "logstash_node_stats", "arguments": {"human": true}}}
```

#### 5. Get All Pipeline Statistics:
```json
{"jsonrpc": "2.0", "id": 6, "method": "tools/call", "params": {"name": "logstash_pipelines_stats", "arguments": {"human": true}}}
```

#### 6. Get Specific Pipeline Statistics:
```json
{"jsonrpc": "2.0", "id": 7, "method": "tools/call", "params": {"name": "logstash_pipeline_stats", "arguments": {"id": "main", "human": true}}}
```

#### 7. Get Hot Threads (Performance Debugging):
```json
{"jsonrpc": "2.0", "id": 8, "method": "tools/call", "params": {"name": "logstash_hot_threads", "arguments": {"threads": 3, "human": true}}}
```

#### 8. List Installed Plugins:
```json
{"jsonrpc": "2.0", "id": 9, "method": "tools/call", "params": {"name": "logstash_plugins", "arguments": {}}}
```

#### 9. Get JVM Statistics:
```json
{"jsonrpc": "2.0", "id": 10, "method": "tools/call", "params": {"name": "logstash_jvm_stats", "arguments": {"human": true}}}
```

#### 10. List Grok Patterns:
```json
{"jsonrpc": "2.0", "id": 11, "method": "tools/call", "params": {"name": "logstash_grok_patterns", "arguments": {}}}
```

#### 11. Reload Pipeline (Replace "main" with actual pipeline ID):
```json
{"jsonrpc": "2.0", "id": 12, "method": "tools/call", "params": {"name": "logstash_reload_pipeline", "arguments": {"id": "main"}}}
```

## 📋 Expected Response Format

Each successful response should follow this format:
```json
{
  "jsonrpc": "2.0",
  "id": <request_id>,
  "result": {
    "content": [
      {
        "type": "text",
        "text": "<tool_output>"
      }
    ]
  }
}
```

## 🔍 Tool Descriptions

### Core Monitoring Tools:
- **logstash_check_connectivity**: Tests connection with detailed diagnostics
- **logstash_node_info**: Basic node information and version
- **logstash_health_check**: Comprehensive health analysis with recommendations
- **logstash_node_stats**: Complete node statistics (JVM, process, events)

### Pipeline Monitoring:
- **logstash_pipelines_stats**: Statistics for all pipelines
- **logstash_pipeline_stats**: Specific pipeline detailed metrics
- **logstash_hot_threads**: Performance debugging information

### System Information:
- **logstash_jvm_stats**: JVM memory and garbage collection details
- **logstash_plugins**: List of all installed plugins
- **logstash_grok_patterns**: Available Grok patterns for parsing

### Management:
- **logstash_reload_pipeline**: Reload pipeline configuration

## 🚨 Troubleshooting

### Common Issues:
1. **Connection Refused**: Ensure Logstash is running on the configured port
2. **Tools Not Found**: Make sure you've run the initialize command first
3. **Invalid Pipeline ID**: Use actual pipeline IDs from your Logstash instance
4. **Permission Errors**: Verify Logstash API is accessible

### Expected Errors:
- If Logstash is not running, connectivity and health checks will show error details
- Invalid pipeline IDs will return 404 errors
- Network issues will be captured with suggestions

## 📊 Health Check Analysis

The health check automatically analyzes:
- **Connectivity**: Tests connection before other checks
- **JVM Memory**: Warns if heap usage > 80%
- **Pipeline Performance**: Detects processing issues
- **Queue Status**: Identifies bottlenecks
- **Recommendations**: Provides actionable suggestions

## 🔧 Configuration

Set environment variables before starting:
```bash
export LOGSTASH_API_BASE="http://your-logstash-host:9600"
python3 logstash_mcp_server.py
```
