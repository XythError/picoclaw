#!/usr/bin/env python3
"""
Pollinations.ai Image Generator
Generates images via the Pollinations.ai API (gen.pollinations.ai).
Supports imagen-4 (premium, 400/day) and flux (free fallback).

Usage:
    python3 pollinations.py generate "prompt text" [options]
    python3 pollinations.py test
    python3 pollinations.py models

Options:
    --model MODEL     Model name (default: imagen-4, fallback: flux)
    --width W         Image width (default: 1024)
    --height H        Image height (default: 768)
    --output FILE     Output path (default: ~/generated_image.jpg)
    --seed N          Random seed for reproducibility
    --nologo          Remove Pollinations watermark
    --enhance         AI prompt enhancement
    --json            Output result as JSON
"""
import sys
import os
import json
import time
import subprocess
import argparse
import urllib.parse

API_BASE = "https://gen.pollinations.ai"
API_KEY = "sk_5wH3UNde43N76PSzslSGvagOskbxd77X"
DEFAULT_MODEL = "imagen-4"
FALLBACK_MODEL = "flux"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds


def generate_image(prompt, model=DEFAULT_MODEL, width=1024, height=768,
                   output=None, seed=None, nologo=False, enhance=False):
    """Generate an image from a text prompt."""
    if output is None:
        safe_name = prompt[:40].replace(" ", "_").replace("/", "_")
        output = os.path.expanduser(f"~/{safe_name}.jpg")

    # URL-encode the prompt (spaces -> %20)
    encoded_prompt = urllib.parse.quote(prompt, safe="")

    # Build URL with parameters
    params = {
        "width": width,
        "height": height,
        "model": model,
        "nologo": "true" if nologo else "false",
        "enhance": "true" if enhance else "false",
    }
    if seed is not None:
        params["seed"] = seed

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{API_BASE}/image/{encoded_prompt}?{query}"

    # Try with primary model, fall back if needed
    for attempt in range(MAX_RETRIES + 1):
        current_model = model if attempt < MAX_RETRIES else FALLBACK_MODEL
        if attempt == MAX_RETRIES and model != FALLBACK_MODEL:
            # Switch to fallback model
            params["model"] = FALLBACK_MODEL
            query = "&".join(f"{k}={v}" for k, v in params.items())
            url = f"{API_BASE}/image/{encoded_prompt}?{query}"
            current_model = FALLBACK_MODEL

        cmd = [
            "curl", "-s", "-L",
            "-H", f"Authorization: Bearer {API_KEY}",
            "-o", output,
            "-w", "%{http_code}|%{size_download}|%{content_type}",
            "--max-time", "60",
            url
        ]

        result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
        status_line = result.stdout.strip()

        parts = status_line.split("|")
        http_code = int(parts[0]) if parts[0].isdigit() else 0
        size = int(float(parts[1])) if len(parts) > 1 and parts[1].replace(".", "").isdigit() else 0
        content_type = parts[2] if len(parts) > 2 else ""

        if http_code == 200 and size > 1000 and "image" in content_type:
            return {
                "success": True,
                "path": output,
                "size_bytes": size,
                "model": current_model,
                "prompt": prompt,
                "width": width,
                "height": height,
                "url": url,
            }

        # Check if it's a rate limit / retryable error
        if http_code in (429, 502, 503) and attempt < MAX_RETRIES:
            delay = RETRY_DELAY * (attempt + 1)
            time.sleep(delay)
            continue

        # Read error response if it's JSON
        error_msg = f"HTTP {http_code}"
        if os.path.exists(output) and size > 0:
            try:
                with open(output, "r") as f:
                    err_data = json.load(f)
                    error_msg = err_data.get("error", {}).get("message", str(err_data))[:200]
                os.remove(output)
            except (json.JSONDecodeError, UnicodeDecodeError):
                pass

        if attempt < MAX_RETRIES:
            time.sleep(RETRY_DELAY)
            continue

    return {
        "success": False,
        "error": error_msg,
        "model": current_model,
        "prompt": prompt,
    }


def get_image_url(prompt, model=DEFAULT_MODEL, width=1024, height=768,
                  nologo=True, enhance=False, seed=None):
    """Return a direct URL for embedding in markdown (no download needed)."""
    encoded_prompt = urllib.parse.quote(prompt, safe="")
    params = f"width={width}&height={height}&model={model}&nologo={'true' if nologo else 'false'}"
    if enhance:
        params += "&enhance=true"
    if seed is not None:
        params += f"&seed={seed}"
    return f"{API_BASE}/image/{encoded_prompt}?{params}"


def list_models():
    """List available image generation models."""
    try:
        result = subprocess.run(
            ["curl", "-s", f"{API_BASE}/models"],
            capture_output=True, text=True, timeout=10
        )
        models = json.loads(result.stdout)
        img_models = []
        for m in models:
            outputs = [str(x).lower() for x in m.get("output_modalities", [])]
            if "image" in outputs:
                img_models.append({
                    "name": m["name"],
                    "description": m.get("description", ""),
                })
        return img_models
    except Exception as e:
        return [{"error": str(e)}]


def test_api():
    """Quick API connectivity test."""
    print("Testing Pollinations.ai API...")

    # Test 1: flux (free, reliable)
    print("\n1. Testing 'flux' model...")
    r = generate_image("a simple test image of bread", model="flux",
                       width=256, height=256, output=os.path.expanduser("~/poll_test_flux.jpg"))
    if r["success"]:
        print(f"   OK: {r['size_bytes']} bytes -> {r['path']}")
    else:
        print(f"   FAIL: {r['error']}")

    time.sleep(2)

    # Test 2: imagen-4 (premium)
    print("\n2. Testing 'imagen-4' model...")
    r = generate_image("a simple test image of bread", model="imagen-4",
                       width=256, height=256, output=os.path.expanduser("~/poll_test_imagen4.jpg"))
    if r["success"]:
        print(f"   OK: {r['size_bytes']} bytes -> {r['path']}")
    else:
        print(f"   FAIL: {r['error']} (will fallback to flux in production)")

    # Test 3: URL generation
    print("\n3. URL generation test:")
    url = get_image_url("golden retriever puppy", model="imagen-4")
    print(f"   {url}")

    print("\nDone.")


def main():
    parser = argparse.ArgumentParser(description="Pollinations.ai Image Generator")
    subparsers = parser.add_subparsers(dest="command")

    # generate
    gen = subparsers.add_parser("generate", help="Generate an image")
    gen.add_argument("prompt", help="Image description (English)")
    gen.add_argument("--model", default=DEFAULT_MODEL, help=f"Model (default: {DEFAULT_MODEL})")
    gen.add_argument("--width", type=int, default=1024, help="Width (default: 1024)")
    gen.add_argument("--height", type=int, default=768, help="Height (default: 768)")
    gen.add_argument("--output", help="Output file path")
    gen.add_argument("--seed", type=int, help="Random seed")
    gen.add_argument("--nologo", action="store_true", help="Remove watermark")
    gen.add_argument("--enhance", action="store_true", help="AI prompt enhancement")
    gen.add_argument("--json", action="store_true", dest="as_json", help="JSON output")

    # url - just return the URL without downloading
    url_cmd = subparsers.add_parser("url", help="Get image URL without downloading")
    url_cmd.add_argument("prompt", help="Image description (English)")
    url_cmd.add_argument("--model", default=DEFAULT_MODEL)
    url_cmd.add_argument("--width", type=int, default=1024)
    url_cmd.add_argument("--height", type=int, default=768)
    url_cmd.add_argument("--nologo", action="store_true")
    url_cmd.add_argument("--enhance", action="store_true")
    url_cmd.add_argument("--seed", type=int)

    # test
    subparsers.add_parser("test", help="Run API test")

    # models
    subparsers.add_parser("models", help="List available image models")

    args = parser.parse_args()

    if args.command == "generate":
        result = generate_image(
            args.prompt, model=args.model, width=args.width, height=args.height,
            output=args.output, seed=args.seed, nologo=args.nologo, enhance=args.enhance
        )
        if args.as_json:
            print(json.dumps(result, indent=2))
        elif result["success"]:
            print(f"Image saved: {result['path']} ({result['size_bytes']} bytes, model: {result['model']})")
        else:
            print(f"Error: {result['error']}", file=sys.stderr)
            sys.exit(1)

    elif args.command == "url":
        url = get_image_url(
            args.prompt, model=args.model, width=args.width, height=args.height,
            nologo=args.nologo, enhance=args.enhance, seed=args.seed
        )
        print(url)

    elif args.command == "test":
        test_api()

    elif args.command == "models":
        models = list_models()
        if models and "error" not in models[0]:
            for m in models:
                print(f"  {m['name']:30s} {m['description'][:60]}")
        else:
            print(f"Error: {models}")

    else:
        parser.print_help()


if __name__ == "__main__":
    main()
