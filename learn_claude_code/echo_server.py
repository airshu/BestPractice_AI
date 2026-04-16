#!/usr/bin/env python3
"""MCP Echo Server - 返回收到的消息（调试输出到 stderr）"""
import json
import sys

def debug(msg):
    """调试信息输出到 stderr，不干扰 stdout"""
    print(f"[echo] {msg}", file=sys.stderr, flush=True)

def send_response(msg):
    """发送 JSON-RPC 响应（输出到 stdout）"""
    print(json.dumps(msg), flush=True)

def main():
    debug("启动，等待请求...")
    
    while True:
        line = sys.stdin.readline()
        if not line:
            debug("STDIN 关闭，退出")
            break
        
        debug(f"收到: {line.strip()[:100]}")
        
        try:
            req = json.loads(line.strip())
            method = req.get("method", "")
            req_id = req.get("id")
            
            debug(f"处理 method: {method}")
            
            if method == "initialize":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "protocolVersion": "2024-11-05",
                        "capabilities": {"tools": {}},
                        "serverInfo": {"name": "echo-server", "version": "1.0"}
                    }
                })
            
            elif method == "notifications/initialized":
                debug("收到 initialized 通知（无需回复）")
            
            elif method == "tools/list":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "tools": [
                            {
                                "name": "echo",
                                "description": "Echoes back the input message",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "message": {"type": "string"}
                                    },
                                    "required": ["message"]
                                }
                            },
                            {
                                "name": "uppercase",
                                "description": "Converts text to uppercase",
                                "inputSchema": {
                                    "type": "object",
                                    "properties": {
                                        "text": {"type": "string"}
                                    },
                                    "required": ["text"]
                                }
                            }
                        ]
                    }
                })
            
            elif method == "tools/call":
                tool_name = req.get("params", {}).get("name", "")
                arguments = req.get("params", {}).get("arguments", {})
                
                debug(f"调用工具: {tool_name}, 参数: {arguments}")
                
                if tool_name == "echo":
                    message = arguments.get("message", "")
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": f"[echo] {message}"}]
                        }
                    })
                
                elif tool_name == "uppercase":
                    text = arguments.get("text", "")
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "result": {
                            "content": [{"type": "text", "text": text.upper()}]
                        }
                    })
                else:
                    send_response({
                        "jsonrpc": "2.0",
                        "id": req_id,
                        "error": {"code": -32601, "message": f"Unknown tool: {tool_name}"}
                    })
            
            elif method == "shutdown":
                send_response({
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {}
                })
                debug("收到 shutdown，退出")
                break
            
            else:
                debug(f"未知 method: {method}")
        
        except json.JSONDecodeError as e:
            debug(f"JSON 解析错误: {e}")
        except Exception as e:
            debug(f"错误: {e}")

if __name__ == "__main__":
    main()
