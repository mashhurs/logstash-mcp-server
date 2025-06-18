#!/usr/bin/env python3
"""
Web UI for Logstash MCP Server

A simple web interface to interact with Logstash directly.
"""

import json
import asyncio
from flask import Flask, render_template, request, jsonify
import aiohttp
import os
from urllib.parse import urljoin

app = Flask(__name__)

# Logstash configuration
LOGSTASH_BASE_URL = os.getenv("LOGSTASH_API_BASE", "http://localhost:9600")

class LogstashClient:
    def __init__(self):
        self.base_url = LOGSTASH_BASE_URL
        
    async def make_request(self, endpoint: str, method: str = "GET", data=None):
        """Make HTTP request to Logstash API"""
        url = urljoin(self.base_url, endpoint)
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.request(method, url, json=data) as response:
                    if response.status == 200:
                        return {"success": True, "data": await response.json()}
                    else:
                        error_text = await response.text()
                        return {"success": False, "error": f"HTTP {response.status}: {error_text}"}
        except Exception as e:
            return {"success": False, "error": f"Connection failed: {str(e)}"}
    
    async def check_connectivity(self):
        """Check connectivity to Logstash instance"""
        try:
            result = await self.make_request("/_node")
            if result["success"]:
                data = result["data"]
                return {
                    "status": "connected",
                    "url": self.base_url,
                    "version": data.get("version", "unknown"),
                    "host": data.get("host", "unknown"),
                    "id": data.get("id", "unknown"),
                    "status_color": data.get("status", "unknown")
                }
            else:
                return {
                    "status": "error",
                    "url": self.base_url,
                    "error": result["error"]
                }
        except Exception as e:
            return {
                "status": "unreachable",
                "url": self.base_url,
                "error": str(e)
            }
    
    async def get_node_info(self):
        """Get Logstash node information"""
        result = await self.make_request("/_node")
        return result
    
    async def get_node_stats(self, human=True):
        """Get comprehensive node statistics"""
        endpoint = "/_node/stats" + ("?human=true" if human else "")
        result = await self.make_request(endpoint)
        return result
    
    async def get_pipelines_stats(self, human=True):
        """Get statistics for all pipelines"""
        endpoint = "/_node/stats/pipelines" + ("?human=true" if human else "")
        result = await self.make_request(endpoint)
        return result
    
    async def get_pipeline_stats(self, pipeline_id, human=True):
        """Get statistics for a specific pipeline"""
        endpoint = f"/_node/stats/pipelines/{pipeline_id}" + ("?human=true" if human else "")
        result = await self.make_request(endpoint)
        return result
    
    async def get_hot_threads(self, threads=3, human=True):
        """Get hot threads information"""
        endpoint = f"/_node/hot_threads?threads={threads}" + ("&human=true" if human else "")
        result = await self.make_request(endpoint)
        return result
    
    async def get_plugins(self):
        """List all installed plugins"""
        result = await self.make_request("/_node/plugins")
        return result
    
    async def check_backpressure(self, human=True):
        """Check queue backpressure metrics"""
        endpoint = "/_node/stats/flow" + ("?human=true" if human else "")
        result = await self.make_request(endpoint)
        
        if result["success"]:
            flow_stats = result["data"]
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
                    "success": True,
                    "data": {
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
                }
            else:
                return {"success": False, "error": "Backpressure data not available"}
        else:
            return result
    
    async def get_jvm_stats(self, human=True):
        """Get JVM statistics"""
        endpoint = "/_node/stats/jvm" + ("?human=true" if human else "")
        result = await self.make_request(endpoint)
        return result
    
    async def get_health_report(self):
        """Get detailed health report"""
        result = await self.make_request("/_health_report")
        return result
    
    async def get_flow_metrics(self, human=True):
        """Get flow metrics including throughput, backpressure, and worker concurrency"""
        endpoint = "/_node/stats" + ("?human=true" if human else "")
        result = await self.make_request(endpoint)
        
        if result["success"]:
            full_stats = result["data"]
            flow_metrics = full_stats.get("flow", {})
            if flow_metrics:
                return {
                    "success": True,
                    "data": {
                        "timestamp": full_stats.get("timestamp"),
                        "flow_metrics": flow_metrics,
                        "summary": {
                            "current_worker_concurrency": flow_metrics.get("worker_concurrency", {}).get("current", 0),
                            "current_queue_backpressure": flow_metrics.get("queue_backpressure", {}).get("current", 0),
                            "input_throughput": flow_metrics.get("input_throughput", {}).get("current", 0),
                            "output_throughput": flow_metrics.get("output_throughput", {}).get("current", 0)
                        }
                    }
                }
            else:
                return {"success": False, "error": "Flow metrics not available"}
        else:
            return result
    
    async def health_check(self):
        """Perform comprehensive health check"""
        try:
            health_status = {
                "overall_status": "healthy",
                "timestamp": None,
                "logstash_version": None,
                "issues": [],
                "recommendations": []
            }
            
            # Check connectivity
            connectivity = await self.check_connectivity()
            if connectivity["status"] != "connected":
                health_status["overall_status"] = "unhealthy"
                health_status["issues"].append(f"Connectivity issue: {connectivity['error']}")
                return health_status
            
            # Get node info
            node_result = await self.get_node_info()
            if node_result["success"]:
                node_info = node_result["data"]
                health_status["logstash_version"] = node_info.get("version", "unknown")
                health_status["timestamp"] = node_info.get("timestamp")
            
            # Get node stats for analysis
            stats_result = await self.get_node_stats()
            if stats_result["success"]:
                node_stats = stats_result["data"]
                
                # Check JVM heap usage
                jvm_stats = node_stats.get("jvm", {})
                if isinstance(jvm_stats, dict) and "mem" in jvm_stats:
                    heap_percent = jvm_stats["mem"].get("heap_used_percent", 0)
                    if heap_percent > 80:
                        health_status["issues"].append(f"High JVM heap usage: {heap_percent}%")
                        health_status["recommendations"].append("Consider increasing JVM heap size")
                        health_status["overall_status"] = "warning"
            
            return health_status
            
        except Exception as e:
            return {
                "overall_status": "unhealthy",
                "error": str(e),
                "timestamp": None
            }

# Global client instance
logstash_client = LogstashClient()

def get_available_tools():
    """Get list of available tools"""
    return [
        {
            "name": "logstash_check_connectivity", 
            "description": "Check connectivity to Logstash instance",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "logstash_node_info", 
            "description": "Get Logstash node information",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "logstash_node_stats", 
            "description": "Get comprehensive node statistics",
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
            "description": "Get statistics for all pipelines",
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
            "description": "Get statistics for specific pipeline",
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
            "description": "Get hot threads for performance debugging",
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
            "description": "List all installed plugins",
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
            "description": "Perform comprehensive health check",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "logstash_jvm_stats", 
            "description": "Get detailed JVM statistics",
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
            "description": "Get detailed health report",
            "inputSchema": {
                "type": "object",
                "properties": {},
                "required": []
            }
        },
        {
            "name": "flow_metrics", 
            "description": "Get flow metrics including throughput, backpressure, and worker concurrency. Reference: https://www.elastic.co/docs/api/doc/logstash/operation/operation-nodestatsflow",
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

@app.route('/')
def index():
    """Main UI page"""
    return render_template('index.html')

@app.route('/start_server', methods=['POST'])
def start_server():
    """Start the Logstash server"""
    # No need to start the server as we are making direct API calls
    return jsonify({"success": True, "initialized": True})

@app.route('/list_tools', methods=['GET'])
def list_tools():
    """Get list of available tools"""
    return jsonify({
        "result": {
            "tools": get_available_tools()
        }
    })

@app.route('/call_tool', methods=['POST'])
def call_tool():
    """Call a specific tool"""
    data = request.json
    tool_name = data.get('name')
    arguments = data.get('arguments', {})
    
    try:
        if tool_name == "logstash_check_connectivity":
            result = asyncio.run(logstash_client.check_connectivity())
        elif tool_name == "logstash_node_info":
            result = asyncio.run(logstash_client.get_node_info())
        elif tool_name == "logstash_node_stats":
            result = asyncio.run(logstash_client.get_node_stats())
        elif tool_name == "logstash_pipelines_stats":
            result = asyncio.run(logstash_client.get_pipelines_stats())
        elif tool_name == "logstash_pipeline_stats":
            pipeline_id = arguments.get("id")
            if not pipeline_id:
                raise ValueError("Pipeline ID is required")
            result = asyncio.run(logstash_client.get_pipeline_stats(pipeline_id))
        elif tool_name == "logstash_hot_threads":
            threads = arguments.get("threads", 3)
            result = asyncio.run(logstash_client.get_hot_threads(threads))
        elif tool_name == "logstash_plugins":
            result = asyncio.run(logstash_client.get_plugins())
        elif tool_name == "check_backpressure":
            result = asyncio.run(logstash_client.check_backpressure())
        elif tool_name == "logstash_health_check":
            result = asyncio.run(logstash_client.health_check())
        elif tool_name == "logstash_jvm_stats":
            result = asyncio.run(logstash_client.get_jvm_stats())
        elif tool_name == "logstash_health_report":
            result = asyncio.run(logstash_client.get_health_report())
        elif tool_name == "flow_metrics":
            result = asyncio.run(logstash_client.get_flow_metrics())
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
        
        # Format response to match MCP format expected by frontend
        return jsonify({
            "result": {
                "content": [
                    {
                        "type": "text",
                        "text": json.dumps(result, indent=2)
                    }
                ]
            }
        })
    
    except Exception as e:
        return jsonify({
            "error": {
                "message": str(e)
            }
        })

@app.route('/server_status', methods=['GET'])
def server_status():
    """Get server status"""
    # No need to check server status as we are making direct API calls
    return jsonify({
        "running": True,
        "initialized": True
    })

if __name__ == '__main__':
    try:
        print("Starting Logstash MCP Web UI")
        print("Open http://localhost:5001 in your browser")
        app.run(debug=True, host='0.0.0.0', port=5001)
    finally:
        pass
