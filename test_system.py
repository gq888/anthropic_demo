#!/usr/bin/env python3
"""
Test script to monitor the multi-agent research system
"""
import asyncio
import json
import time
import websockets
import requests

async def test_research_system():
    # Start a research task
    print("Starting research task...")
    response = requests.post(
        "http://localhost:8001/research",
        json={
            "query": "What are the key benefits of renewable energy?",
            "max_subagents": 2,
            "search_depth": "medium"
        }
    )
    
    if response.status_code != 200:
        print(f"Failed to start research: {response.text}")
        return
    
    result = response.json()
    run_id = result["run_id"]
    print(f"Research started with run ID: {run_id}")
    
    # Connect to WebSocket for real-time updates
    ws_url = f"ws://localhost:8001/ws/{run_id}"
    
    try:
        async with websockets.connect(ws_url) as websocket:
            print("Connected to WebSocket")
            
            # Send initial message
            await websocket.send(json.dumps({"type": "ping"}))
            
            # Listen for updates
            start_time = time.time()
            while time.time() - start_time < 60:  # Run for max 60 seconds
                try:
                    message = await asyncio.wait_for(websocket.recv(), timeout=5.0)
                    data = json.loads(message)
                    print(f"Received: {data}")
                    
                    # Check if research is complete
                    if data.get("type") == "agent_event" and data.get("data", {}).get("event_type") == "research_complete":
                        print("Research completed!")
                        break
                        
                except asyncio.TimeoutError:
                    # Check research status
                    status_response = requests.get(f"http://localhost:8001/runs/{run_id}")
                    if status_response.status_code == 200:
                        status = status_response.json()
                        print(f"Current status: {status['status']}")
                        if status['status'] in ['completed', 'failed']:
                            break
                    
                    # Send ping to keep connection alive
                    await websocket.send(json.dumps({"type": "ping"}))
                    
    except Exception as e:
        print(f"WebSocket error: {e}")
    
    # Get final results
    final_response = requests.get(f"http://localhost:8001/runs/{run_id}")
    if final_response.status_code == 200:
        final_data = final_response.json()
        print(f"\nFinal status: {final_data['status']}")
        if final_data.get('final_report'):
            print(f"Report length: {len(final_data['final_report'])} characters")
            print(f"Citations: {len(final_data['citations'])}")
        if final_data.get('subagents'):
            print(f"Subagents used: {len(final_data['subagents'])}")

if __name__ == "__main__":
    asyncio.run(test_research_system())