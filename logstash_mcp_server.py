#!/usr/bin/env python3
"""
Logstash MCP Server

A Model Context Protocol server for interacting with Logstash instances.
Provides tools for monitoring, configuration management, and pipeline operations.
"""

import json
import logging
import os
import sys
from typing import Any, Dict, Optional
from urllib.parse import urljoin

import aiohttp
import asyncio

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("logstash-mcp")

# Default Logstash configuration
DEFAULT_LOGSTASH_HOST = "localhost"
DEFAULT_LOGSTASH_PORT = 9600
DEFAULT_LOGSTASH_API_BASE = f"http://{DEFAULT_LOGSTASH_HOST}:{DEFAULT_LOGSTASH_PORT}"

# Global configuration
LOGSTASH_BASE_URL = os.getenv("LOGSTASH_API_BASE", DEFAULT_LOGSTASH_API_BASE)

# Server state
is_initialized = False

async def make_request(endpoint: str, method: str = "GET", data: Optional[Dict] = None) -> Dict[str, Any]:
    """Make HTTP request to Logstash API"""
    url = urljoin(LOGSTASH_BASE_URL, endpoint)
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.request(method, url, json=data) as response:
                if response.status == 200:
                    return await response.json()
                else:
                    error_text = await response.text()
                    raise Exception(f"HTTP {response.status}: {error_text}")
    except aiohttp.ClientError as e:
        raise Exception(f"Failed to connect to Logstash at {url}: {str(e)}")

async def check_connectivity() -> Dict[str, Any]:
    """Check connectivity to Logstash instance"""
    try:
        url = urljoin(LOGSTASH_BASE_URL, "/_node")
        
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=5)) as session:
            async with session.get(url) as response:
                if response.status == 200:
                    node_info = await response.json()
                    return {
                        "status": "connected",
                        "url": LOGSTASH_BASE_URL,
                        "version": node_info.get("version", "unknown"),
                        "host": node_info.get("host", "unknown"),
                        "response_time_ms": response.headers.get("x-response-time", "unknown"),
                        "timestamp": node_info.get("timestamp") or "unknown"
                    }
                else:
                    return {
                        "status": "error",
                        "url": LOGSTASH_BASE_URL,
                        "error": f"HTTP {response.status}",
                        "message": await response.text()
                    }
    except Exception as e:
        return {
            "status": "unreachable",
            "url": LOGSTASH_BASE_URL,
            "error": str(e),
            "suggestion": "Verify Logstash URL and network connectivity"
        }

async def health_check() -> Dict[str, Any]:
    """Perform comprehensive health check"""
    try:
        health_status = {
            "overall_status": "healthy",
            "timestamp": None,
            "logstash_version": None,
            "issues": [],
            "recommendations": []
        }
        
        # Check connectivity first
        connectivity = await check_connectivity()
        if connectivity["status"] != "connected":
            health_status["overall_status"] = "unhealthy"
            health_status["issues"].append(f"Connectivity issue: {connectivity['error']}")
            health_status["recommendations"].append(connectivity.get("suggestion", "Check Logstash connectivity"))
            return health_status
        
        # Get node info
        node_info = await make_request("/_node")
        health_status["logstash_version"] = node_info.get("version", "unknown")
        health_status["timestamp"] = node_info.get("timestamp")
        
        # Get node stats for analysis
        node_stats = await make_request("/_node/stats?human=true")
        
        # Check JVM heap usage
        jvm_stats = node_stats.get("jvm", {})
        if isinstance(jvm_stats, dict) and "mem" in jvm_stats:
            heap_percent = jvm_stats["mem"].get("heap_used_percent", 0)
            if heap_percent > 80:
                health_status["issues"].append(f"High JVM heap usage: {heap_percent}%")
                health_status["recommendations"].append("Consider increasing JVM heap size or optimizing memory usage")
                health_status["overall_status"] = "warning"
        
        # Check pipeline performance
        try:
            pipeline_stats = await make_request("/_node/stats/pipelines?human=true")
            pipelines = pipeline_stats.get("pipelines", {})
            for pipeline_id, stats in pipelines.items():
                if isinstance(stats, dict) and "events" in stats:
                    events = stats["events"]
                    filtered = events.get("filtered", 0)
                    out = events.get("out", 0)
                    if filtered > 0 and out == 0:
                        health_status["issues"].append(f"Pipeline {pipeline_id} has filtered events but no output")
                        health_status["recommendations"].append(f"Check pipeline {pipeline_id} configuration for output issues")
                        health_status["overall_status"] = "warning"
        except:
            pass  # Pipeline stats might not be available
            
        return health_status
        
    except Exception as e:
        return {
            "overall_status": "unhealthy",
            "error": str(e),
            "timestamp": None
        }

def get_tools():
    """Get list of available tools"""
    return [
        {
            "name": "logstash_check_connectivity",
            "description": "Check connectivity to Logstash instance with detailed diagnostics",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "logstash_node_info",
            "description": "Get Logstash node information including version and settings",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "logstash_node_stats",
            "description": "Get comprehensive node statistics including JVM and process metrics",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "human": {
                        "type": "boolean",
                        "description": "Format output for human readability",
                        "default": True
                    }
                },
                "required": []
            }
        },
        {
            "name": "logstash_pipelines_stats",
            "description": "Get statistics for all Logstash pipelines",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "human": {
                        "type": "boolean",
                        "description": "Format output for human readability",
                        "default": True
                    }
                },
                "required": []
            }
        },
        {
            "name": "logstash_pipeline_stats",
            "description": "Get statistics for a specific pipeline",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "id": {
                        "type": "string",
                        "description": "Pipeline ID to get statistics for"
                    },
                    "human": {
                        "type": "boolean",
                        "description": "Format output for human readability",
                        "default": True
                    }
                },
                "required": ["id"]
            }
        },
        {
            "name": "logstash_hot_threads",
            "description": "Get hot threads information for performance debugging",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "threads": {
                        "type": "integer",
                        "description": "Number of hot threads to return",
                        "default": 3
                    },
                    "human": {
                        "type": "boolean",
                        "description": "Format output for human readability",
                        "default": True
                    }
                },
                "required": []
            }
        },
        {
            "name": "logstash_plugins",
            "description": "List all installed Logstash plugins",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "check_backpressure",
            "description": "Check queue backpressure metrics to monitor pipeline performance and congestion",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "human": {
                        "type": "boolean",
                        "description": "Format output for human readability",
                        "default": True
                    }
                },
                "required": []
            }
        },
        {
            "name": "logstash_health_check",
            "description": "Perform comprehensive health check with analysis and recommendations",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "logstash_jvm_stats",
            "description": "Get detailed JVM statistics for memory analysis",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "human": {
                        "type": "boolean",
                        "description": "Format output for human readability",
                        "default": True
                    }
                },
                "required": []
            }
        },
        {
            "name": "logstash_health_report",
            "description": "Get detailed health report from Logstash",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "flow_metrics",
            "description": "Get detailed flow metrics including throughput, backpressure, and worker concurrency. Reference: https://www.elastic.co/docs/api/doc/logstash/operation/operation-nodestatsflow",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "human": {
                        "type": "boolean",
                        "description": "Format output for human readability",
                        "default": True
                    }
                },
                "required": []
            }
        }
    ]

async def handle_tool_call(name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
    """Handle tool calls"""
    try:
        if name == "logstash_check_connectivity":
            return await check_connectivity()
        elif name == "logstash_node_info":
            return await make_request("/_node")
        elif name == "logstash_node_stats":
            human = arguments.get("human", True)
            endpoint = "/_node/stats" + ("?human=true" if human else "")
            return await make_request(endpoint)
        elif name == "logstash_pipelines_stats":
            human = arguments.get("human", True)
            endpoint = "/_node/stats/pipelines" + ("?human=true" if human else "")
            return await make_request(endpoint)
        elif name == "logstash_pipeline_stats":
            pipeline_id = arguments.get("id")
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")
            human = arguments.get("human", True)
            endpoint = f"/_node/stats/pipelines/{pipeline_id}" + ("?human=true" if human else "")
            return await make_request(endpoint)
        elif name == "logstash_hot_threads":
            threads = arguments.get("threads", 3)
            human = arguments.get("human", True)
            endpoint = f"/_node/hot_threads?threads={threads}" + ("&human=true" if human else "")
            return await make_request(endpoint)
        elif name == "logstash_plugins":
            return await make_request("/_node/plugins")
        elif name == "check_backpressure":
            # Get flow stats and extract backpressure data
            human = arguments.get("human", True)
            endpoint = "/_node/stats/flow" + ("?human=true" if human else "")
            flow_stats = await make_request(endpoint)
            
            # Extract and format backpressure data
            flow_data = flow_stats.get("flow", {})
            backpressure_data = flow_data.get("queue_backpressure", {})
            
            if backpressure_data:
                # Add analysis of backpressure levels
                current_backpressure = backpressure_data.get("current", 0)
                status = "healthy"
                recommendation = "Queue backpressure is at normal levels"
                
                if current_backpressure > 0.1:  # 10%
                    status = "critical"
                    recommendation = "High backpressure detected! Consider scaling workers or optimizing filters"
                elif current_backpressure > 0.05:  # 5%
                    status = "warning"
                    recommendation = "Moderate backpressure detected. Monitor closely and consider optimization"
                elif current_backpressure > 0.01:  # 1%
                    status = "caution"
                    recommendation = "Slight backpressure detected. Normal under heavy load"
                
                return {
                    "timestamp": flow_stats.get("timestamp"),
                    "status": status,
                    "recommendation": recommendation,
                    "queue_backpressure": backpressure_data,
                    "current_backpressure_percent": f"{current_backpressure * 100:.4f}%",
                    "analysis": {
                        "trend_1min": backpressure_data.get("last_1_minute", 0),
                        "trend_5min": backpressure_data.get("last_5_minutes", 0),
                        "trend_15min": backpressure_data.get("last_15_minutes", 0),
                        "baseline": backpressure_data.get("lifetime", 0)
                    }
                }
            else:
                return {"error": "Backpressure data not available"}
        elif name == "logstash_health_check":
            return await health_check()
        elif name == "logstash_jvm_stats":
            human = arguments.get("human", True)
            endpoint = "/_node/stats/jvm" + ("?human=true" if human else "")
            return await make_request(endpoint)
        elif name == "logstash_health_report":
            return await make_request("/_health_report")
        elif name == "flow_metrics":
            # Get full node stats and extract flow metrics
            endpoint = "/_node/stats" + ("?human=true" if arguments.get("human", True) else "")
            full_stats = await make_request(endpoint)
            
            # Extract and format flow metrics
            flow_metrics = full_stats.get("flow", {})
            if flow_metrics:
                return {
                    "timestamp": full_stats.get("timestamp"),
                    "flow_metrics": flow_metrics,
                    "summary": {
                        "current_worker_concurrency": flow_metrics.get("worker_concurrency", {}).get("current", 0),
                        "current_queue_backpressure": flow_metrics.get("queue_backpressure", {}).get("current", 0),
                        "input_throughput": flow_metrics.get("input_throughput", {}).get("current", 0),
                        "output_throughput": flow_metrics.get("output_throughput", {}).get("current", 0)
                    }
                }
            else:
                return {"error": "Flow metrics not available"}
        else:
            raise ValueError(f"Unknown tool: {name}")
            
    except Exception as e:
        return {
            "error": str(e),
            "tool": name,
            "arguments": arguments
        }

async def handle_request(request_data: Dict[str, Any]) -> Dict[str, Any]:
    """Handle JSON-RPC requests"""
    global is_initialized
    
    method = request_data.get("method")
    request_id = request_data.get("id")
    params = request_data.get("params", {})
    
    try:
        if method == "initialize":
            is_initialized = True
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "capabilities": {},
                    "serverInfo": {
                        "name": "logstash-mcp",
                        "version": "1.0.0"
                    }
                }
            }
        
        elif method == "tools/list":
            if not is_initialized:
                raise Exception("Server not initialized")
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "tools": get_tools()
                }
            }
        
        elif method == "tools/call":
            if not is_initialized:
                raise Exception("Server not initialized")
            tool_name = params.get("name")
            arguments = params.get("arguments", {})
            result = await handle_tool_call(tool_name, arguments)
            return {
                "jsonrpc": "2.0",
                "id": request_id,
                "result": {
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(result, indent=2)
                        }
                    ]
                }
            }
        
        else:
            raise Exception(f"Unknown method: {method}")
            
    except Exception as e:
        return {
            "jsonrpc": "2.0",
            "id": request_id,
            "error": {
                "code": -32602,
                "message": str(e)
            }
        }

async def main():
    """Main entry point"""
    # Print startup information
    print("🚀 Logstash MCP Server Starting")
    print("=" * 40)
    print(f"📍 Logstash API Base: {LOGSTASH_BASE_URL}")
    print("📡 Protocol: Model Context Protocol (MCP)")
    print("🔌 Communication: stdin/stdout JSON-RPC")
    print()
    
    print("🛠️  Available Tools (12 total):")
    print("-" * 30)
    print("📊 Monitoring:")
    print("   • logstash_check_connectivity - Connection verification")
    print("   • logstash_node_info - Node information and version")
    print("   • logstash_node_stats - Comprehensive statistics")
    print("   • logstash_pipelines_stats - All pipeline metrics")
    print("   • logstash_jvm_stats - JVM memory analysis")
    print()
    print("🏥 Health & Diagnostics:")
    print("   • logstash_health_check - Intelligent health analysis")
    print("   • logstash_hot_threads - Performance debugging")
    print()
    print("🔧 Management:")
    print("   • logstash_pipeline_stats - Specific pipeline metrics")
    print("   • logstash_plugins - List installed plugins")
    print("   • check_backpressure - Queue backpressure metrics")
    print("   • logstash_health_report - Detailed health report")
    print("   • flow_metrics - Worker utilization and flow metrics")
    print()
    
    print("📋 How to Call Tools:")
    print("-" * 20)
    print("1️⃣  Initialize MCP session (COPY-PASTE READY):")
    print('{"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "test-client", "version": "1.0.0"}}}')
    print()
    print("2️⃣  List all tools (COPY-PASTE READY):")
    print('{"jsonrpc": "2.0", "id": 1, "method": "tools/list"}')
    print()
    print("3️⃣  Health check (COPY-PASTE READY):")
    print('{"jsonrpc": "2.0", "id": 2, "method": "tools/call", "params": {"name": "logstash_health_check", "arguments": {}}}')
    print()
    print("4️⃣  Node info (COPY-PASTE READY):")
    print('{"jsonrpc": "2.0", "id": 3, "method": "tools/call", "params": {"name": "logstash_node_info", "arguments": {}}}')
    print()
    print("5️⃣  Connectivity check (COPY-PASTE READY):")
    print('{"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "logstash_check_connectivity", "arguments": {}}}')
    print()
    
    print("🎯 Ready for MCP communication...")
    print("   • Send JSON-RPC messages to stdin")
    print("   • Responses will be sent to stdout")
    print("   • Press Ctrl+C to stop")
    print("=" * 40)
    
    # Handle JSON-RPC requests from stdin
    try:
        while True:
            line = await asyncio.get_event_loop().run_in_executor(None, sys.stdin.readline)
            if not line:
                break
            
            line = line.strip()
            if not line:
                continue
                
            try:
                request = json.loads(line)
                response = await handle_request(request)
                print(json.dumps(response), flush=True)
            except json.JSONDecodeError as e:
                error_response = {
                    "jsonrpc": "2.0",
                    "id": None,
                    "error": {
                        "code": -32700,
                        "message": f"Parse error: {str(e)}"
                    }
                }
                print(json.dumps(error_response), flush=True)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    asyncio.run(main())
