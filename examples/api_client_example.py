#!/usr/bin/env python3
"""
Example usage of the FastLED WASM Server API Client.

This script demonstrates how to use both the async and sync versions
of the API client to interact with a FastLED WASM server.
"""

import asyncio
from pathlib import Path

from fastled_wasm_server.api_client import FastLEDWasmClient, FastLEDWasmSyncClient


async def async_example():
    """Example using the async API client."""
    server_url = "http://localhost:8080"  # Replace with your server URL
    
    async with FastLEDWasmClient(server_url) as client:
        # Health check
        print("=== Health Check ===")
        health = await client.health_check()
        print(f"Server status: {health.status}")
        
        # Get server info
        print("\n=== Server Info ===")
        info = await client.get_info()
        print(f"Available examples: {info.examples}")
        print(f"Available builds: {info.available_builds}")
        print(f"Uptime: {info.uptime}")
        print(f"FastLED version: {info.fastled_version}")
        
        # Get server settings
        print("\n=== Server Settings ===")
        settings = await client.get_settings()
        print(f"Upload limit: {settings.UPLOAD_LIMIT}")
        print(f"Cache enabled: {not settings.NO_SKETCH_CACHE}")
        
        # Check if compiler is in use
        print("\n=== Compiler Status ===")
        compiler_status = await client.is_compiler_in_use()
        print(f"Compiler in use: {compiler_status.in_use}")
        
        # Initialize a project
        print("\n=== Project Initialization ===")
        try:
            project_zip = await client.init_project()
            print(f"Project initialized, ZIP size: {len(project_zip)} bytes")
            
            # Save the project to a file
            with open("fastled_project.zip", "wb") as f:
                f.write(project_zip)
            print("Project saved as fastled_project.zip")
        except Exception as e:
            print(f"Failed to initialize project: {e}")
        
        # Example with specific project
        print("\n=== Initialize with specific example ===")
        try:
            # Get available examples first
            if info.examples:
                example_name = info.examples[0]  # Use first available example
                example_zip = await client.init_project(example=example_name)
                print(f"Example '{example_name}' initialized, ZIP size: {len(example_zip)} bytes")
        except Exception as e:
            print(f"Failed to initialize example: {e}")
        
        # Compile WASM (if you have a file to compile)
        print("\n=== WASM Compilation ===")
        try:
            # This is just an example - you would need an actual .ino file
            # compile_result = await client.compile_wasm(
            #     file_path="path/to/your/sketch.ino",
            #     build="quick"
            # )
            # print(f"Compilation successful, WASM size: {len(compile_result)} bytes")
            print("Skipping compilation - no source file provided")
        except Exception as e:
            print(f"Compilation failed: {e}")
        
        # Stream libfastled compilation
        print("\n=== LibFastLED Compilation (Dry Run) ===")
        try:
            async for output in client.compile_libfastled(build="quick", dry_run=True):
                print(f"Compilation output: {output.strip()}")
        except Exception as e:
            print(f"LibFastLED compilation failed: {e}")


def sync_example():
    """Example using the synchronous API client."""
    server_url = "http://localhost:8080"  # Replace with your server URL
    
    client = FastLEDWasmSyncClient(server_url)
    
    try:
        # Health check
        print("=== Sync Health Check ===")
        health = client.health_check()
        print(f"Server status: {health.status}")
        
        # Get server info
        print("\n=== Sync Server Info ===")
        info = client.get_info()
        print(f"Available examples: {info.examples}")
        print(f"Compile count: {info.compile_count}")
        
        # Check compiler status
        print("\n=== Sync Compiler Status ===")
        compiler_status = client.is_compiler_in_use()
        print(f"Compiler in use: {compiler_status.in_use}")
        
    except Exception as e:
        print(f"Sync client error: {e}")


def compile_from_content_example():
    """Example of compiling from file content without saving to disk."""
    async def _compile_content():
        server_url = "http://localhost:8080"  # Replace with your server URL
        
        # Example Arduino sketch content
        sketch_content = """
#include <FastLED.h>

#define NUM_LEDS 60
#define DATA_PIN 6

CRGB leds[NUM_LEDS];

void setup() {
    FastLED.addLeds<WS2812, DATA_PIN, GRB>(leds, NUM_LEDS);
}

void loop() {
    for (int i = 0; i < NUM_LEDS; i++) {
        leds[i] = CRGB::Red;
        FastLED.show();
        delay(50);
        leds[i] = CRGB::Black;
    }
}
""".encode('utf-8')
        
        async with FastLEDWasmClient(server_url) as client:
            try:
                result = await client.compile_wasm_with_file_content(
                    file_content=sketch_content,
                    filename="example_sketch.ino",
                    build="quick"
                )
                print(f"Compilation from content successful, WASM size: {len(result)} bytes")
                
                # Save the compiled WASM
                with open("compiled_sketch.wasm", "wb") as f:
                    f.write(result)
                print("Compiled WASM saved as compiled_sketch.wasm")
                
            except Exception as e:
                print(f"Compilation from content failed: {e}")
    
    print("\n=== Compile from Content Example ===")
    asyncio.run(_compile_content())


if __name__ == "__main__":
    print("FastLED WASM Server API Client Examples")
    print("=" * 50)
    
    print("\nRunning async example...")
    try:
        asyncio.run(async_example())
    except Exception as e:
        print(f"Async example failed: {e}")
    
    print("\n" + "=" * 50)
    print("\nRunning sync example...")
    try:
        sync_example()
    except Exception as e:
        print(f"Sync example failed: {e}")
    
    print("\n" + "=" * 50)
    print("\nRunning compile from content example...")
    try:
        compile_from_content_example()
    except Exception as e:
        print(f"Compile from content example failed: {e}")