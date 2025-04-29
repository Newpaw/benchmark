#!/usr/bin/env python3
"""
LLM Benchmark Script

A minimalist Python script to benchmark a Language Model's performance metrics,
focusing on latency. Connects to an OpenAI-compatible endpoint and measures
response times across multiple requests.
"""
import argparse
import asyncio
import httpx
import ssl
import statistics
import sys
import time
import traceback
import os
from typing import Dict, List, Any, Optional, Tuple
from dotenv import load_dotenv



# Constants and Configuration
load_dotenv()

DEFAULT_ENDPOINT = os.environ.get("DEFAULT_ENDPOINT", "http://litellm.ai-sandbox.azure.to2cz.cz")
DEFAULT_API_KEY = os.environ.get("DEFAULT_API_KEY", "sk-xxx")
DEFAULT_MODEL = os.environ.get("DEFAULT_MODEL", "gpt-4o")
DEFAULT_NUM_REQUESTS = 10
DEFAULT_PROMPT = "Tell me a short joke"
DEFAULT_TIMEOUT = 30.0  # seconds
DEFAULT_MAX_RETRIES = 3
DEFAULT_RETRY_DELAY = 1.0  # seconds
DEFAULT_REQUEST_DELAY = 2.0  # seconds between requests to avoid rate limiting
DEFAULT_VERIFY_SSL = True


# API Client Functions
async def make_request(
    client: httpx.AsyncClient,
    endpoint: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout: float,
    debug: bool = False,
) -> Tuple[float, Optional[Dict[str, Any]], Optional[Exception]]:
    """
    Make a request to the LLM API and measure the response time.
    
    Args:
        client: The HTTP client
        endpoint: The API endpoint URL
        api_key: The API key for authentication
        model: The model to use
        prompt: The prompt to send
        timeout: Request timeout in seconds
        debug: Whether to print debug information
        
    Returns:
        Tuple of (response_time, response_data, exception)
    """
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}"
    }
    
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.7,
        "max_tokens": 150
    }
    
    if debug:
        print(f"\nDebug: Making request to {endpoint}/v1/chat/completions")
    
    start_time = time.time()
    exception = None
    
    try:
        response = await client.post(
            endpoint + "/v1/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout
        )
        response_time = time.time() - start_time
        
        if response.status_code == 200:
            return response_time, response.json(), None
        else:
            print(f"Error: API returned status code {response.status_code}")
            print(f"Response: {response.text}")
            return response_time, None, None
            
    except httpx.TimeoutException as e:
        print(f"Error: Request timed out after {timeout} seconds")
        return time.time() - start_time, None, e
    except httpx.RequestError as e:
        print(f"Error: Request failed - {str(e)}")
        if debug:
            print(f"Debug: Request error type: {type(e).__name__}")
        return time.time() - start_time, None, e
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        if debug:
            print(f"Debug: Exception traceback:")
            traceback.print_exc()
        return time.time() - start_time, None, e


# Benchmark Runner
async def run_benchmark(
    endpoint: str,
    api_key: str,
    model: str,
    prompt: str,
    num_requests: int,
    timeout: float,
    max_retries: int,
    retry_delay: float,
    request_delay: float = DEFAULT_REQUEST_DELAY,
    verify_ssl: bool = True,
    debug: bool = False,
) -> List[float]:
    """
    Run the benchmark with the specified parameters.
    
    Args:
        endpoint: The API endpoint URL
        api_key: The API key for authentication
        model: The model to use
        prompt: The prompt to send
        num_requests: Number of requests to make
        timeout: Request timeout in seconds
        max_retries: Maximum number of retries for failed requests
        retry_delay: Delay between retries in seconds
        
    Returns:
        List of response times in seconds
    """
    response_times = []
    successful_requests = 0
    
    print(f"\nStarting benchmark with {num_requests} requests to {endpoint}")
    print(f"Model: {model}")
    print(f"Prompt: '{prompt}'")
    print(f"SSL verification: {'Enabled' if verify_ssl else 'Disabled'}")
    print("-" * 50)
    
    # Try alternate protocol if specified
    if debug and endpoint.startswith("https://"):
        print(f"Debug: Also trying HTTP protocol as fallback if HTTPS fails")
    
    async with httpx.AsyncClient(verify=verify_ssl) as client:
        for i in range(num_requests):
            retry_count = 0
            while retry_count <= max_retries:
                print(f"Request {i+1}/{num_requests}", end="", flush=True)
                
                try_endpoint = endpoint
                
                response_time, response_data, exception = await make_request(
                    client, try_endpoint, api_key, model, prompt, timeout, debug
                )
                
                # If HTTPS fails with SSL error and debug is enabled, try HTTP
                if response_data is None and debug and endpoint.startswith("https://"):
                    if exception and (isinstance(exception, (ssl.SSLError, httpx.SSLError)) or "SSL" in str(exception) or "TLS" in str(exception)):
                        http_endpoint = endpoint.replace("https://", "http://")
                        print(f"\nDebug: HTTPS failed with SSL error, trying HTTP: {http_endpoint}")
                        response_time, response_data, http_exception = await make_request(
                            client, http_endpoint, api_key, model, prompt, timeout, debug
                        )
                
                if response_data is not None:
                    response_times.append(response_time)
                    successful_requests += 1
                    print(f" - {response_time:.4f}s")
                    break
                else:
                    retry_count += 1
                    if retry_count <= max_retries:
                        print(f" - Failed, retrying ({retry_count}/{max_retries})...")
                        await asyncio.sleep(retry_delay * retry_count)  # Exponential backoff
                    else:
                        print(f" - Failed after {max_retries} retries")
                        break
                
                # Add delay between requests to avoid rate limiting
                if i < num_requests - 1:
                    delay_msg = f"Waiting {request_delay}s before next request to avoid rate limiting..."
                    print(delay_msg)
                    await asyncio.sleep(request_delay)
    
    print("-" * 50)
    print(f"Completed {successful_requests}/{num_requests} requests successfully")
    
    return response_times


# Statistics Calculation Functions
def calculate_statistics(response_times: List[float]) -> Dict[str, float]:
    """
    Calculate statistics from the response times.
    
    Args:
        response_times: List of response times in seconds
        
    Returns:
        Dictionary of statistics
    """
    if not response_times:
        return {
            "count": 0,
            "min": 0,
            "max": 0,
            "mean": 0,
            "median": 0,
            "stdev": 0,
            "p90": 0,
            "p95": 0,
            "p99": 0,
        }
    
    sorted_times = sorted(response_times)
    count = len(sorted_times)
    
    # Calculate percentiles
    p90_index = int(count * 0.9)
    p95_index = int(count * 0.95)
    p99_index = int(count * 0.99)
    
    return {
        "count": count,
        "min": min(sorted_times),
        "max": max(sorted_times),
        "mean": statistics.mean(sorted_times),
        "median": statistics.median(sorted_times),
        "stdev": statistics.stdev(sorted_times) if count > 1 else 0,
        "p90": sorted_times[p90_index - 1] if count >= 10 else sorted_times[-1],
        "p95": sorted_times[p95_index - 1] if count >= 20 else sorted_times[-1],
        "p99": sorted_times[p99_index - 1] if count >= 100 else sorted_times[-1],
    }


# Results Visualization Functions
def generate_ascii_histogram(response_times: List[float], bins: int = 10) -> str:
    """
    Generate an ASCII histogram of response times.
    
    Args:
        response_times: List of response times in seconds
        bins: Number of bins for the histogram
        
    Returns:
        ASCII histogram as a string
    """
    if not response_times:
        return "No data to display"
    
    min_time = min(response_times)
    max_time = max(response_times)
    
    if min_time == max_time:
        bin_width = 0.1
    else:
        bin_width = (max_time - min_time) / bins
    
    # Create bins
    bin_counts = [0] * bins
    for time in response_times:
        bin_index = min(bins - 1, int((time - min_time) / bin_width))
        bin_counts[bin_index] += 1
    
    # Find the maximum count for scaling
    max_count = max(bin_counts) if bin_counts else 0
    scale_factor = 40 / max_count if max_count > 0 else 1
    
    # Generate the histogram
    histogram = []
    for i, count in enumerate(bin_counts):
        bin_start = min_time + i * bin_width
        bin_end = bin_start + bin_width
        bar = "#" * int(count * scale_factor)
        histogram.append(f"{bin_start:.4f} - {bin_end:.4f} | {bar} ({count})")
    
    return "\n".join(histogram)


def display_results(stats: Dict[str, float], histogram: str) -> None:
    """
    Display the benchmark results.
    
    Args:
        stats: Dictionary of statistics
        histogram: ASCII histogram as a string
    """
    print("\nBenchmark Results:")
    print("-" * 50)
    print(f"Total requests: {stats['count']}")
    print(f"Min latency: {stats['min']:.4f}s")
    print(f"Max latency: {stats['max']:.4f}s")
    print(f"Mean latency: {stats['mean']:.4f}s")
    print(f"Median latency: {stats['median']:.4f}s")
    print(f"Standard deviation: {stats['stdev']:.4f}s")
    print(f"90th percentile: {stats['p90']:.4f}s")
    print(f"95th percentile: {stats['p95']:.4f}s")
    print(f"99th percentile: {stats['p99']:.4f}s")
    print("\nLatency Distribution:")
    print("-" * 50)
    print(histogram)


# Main Function
async def async_main(args: argparse.Namespace) -> None:
    """
    Main async function to run the benchmark.
    
    Args:
        args: Command line arguments
    """
    # Try HTTP if specified
    endpoint = args.endpoint
    if args.try_http and endpoint.startswith("https://"):
        endpoint = endpoint.replace("https://", "http://")
        print(f"Using HTTP instead of HTTPS: {endpoint}")
    
    response_times = await run_benchmark(
        endpoint=endpoint,
        api_key=args.api_key,
        model=args.model,
        prompt=args.prompt,
        num_requests=args.num_requests,
        timeout=args.timeout,
        max_retries=args.max_retries,
        retry_delay=args.retry_delay,
        request_delay=args.request_delay,
        verify_ssl=args.verify_ssl,
        debug=args.debug,
    )
    
    if not response_times:
        print("No successful requests were made. Cannot generate statistics.")
        return
    
    stats = calculate_statistics(response_times)
    histogram = generate_ascii_histogram(response_times)
    display_results(stats, histogram)


def main():
    """
    Entry point for the benchmark script.
    """
    parser = argparse.ArgumentParser(
        description="Benchmark an LLM API for latency performance"
    )
    parser.add_argument(
        "--endpoint", 
        default=DEFAULT_ENDPOINT,
        help=f"API endpoint URL (default: {DEFAULT_ENDPOINT})"
    )
    parser.add_argument(
        "--api-key", 
        default=DEFAULT_API_KEY,
        help="API key for authentication"
    )
    parser.add_argument(
        "--model", 
        default=DEFAULT_MODEL,
        help=f"Model to use (default: {DEFAULT_MODEL})"
    )
    parser.add_argument(
        "--prompt", 
        default=DEFAULT_PROMPT,
        help=f"Prompt to send (default: '{DEFAULT_PROMPT}')"
    )
    parser.add_argument(
        "--num-requests", 
        type=int, 
        default=DEFAULT_NUM_REQUESTS,
        help=f"Number of requests to make (default: {DEFAULT_NUM_REQUESTS})"
    )
    parser.add_argument(
        "--timeout", 
        type=float, 
        default=DEFAULT_TIMEOUT,
        help=f"Request timeout in seconds (default: {DEFAULT_TIMEOUT})"
    )
    parser.add_argument(
        "--max-retries", 
        type=int, 
        default=DEFAULT_MAX_RETRIES,
        help=f"Maximum number of retries for failed requests (default: {DEFAULT_MAX_RETRIES})"
    )
    parser.add_argument(
        "--retry-delay",
        type=float,
        default=DEFAULT_RETRY_DELAY,
        help=f"Base delay between retries in seconds (default: {DEFAULT_RETRY_DELAY})"
    )
    parser.add_argument(
        "--request-delay",
        type=float,
        default=DEFAULT_REQUEST_DELAY,
        help=f"Delay between requests in seconds to avoid rate limiting (default: {DEFAULT_REQUEST_DELAY})"
    )
    parser.add_argument(
        "--no-verify-ssl",
        action="store_false",
        dest="verify_ssl",
        default=DEFAULT_VERIFY_SSL,
        help="Disable SSL certificate verification"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode with additional logging and fallback options"
    )
    parser.add_argument(
        "--try-http",
        action="store_true",
        help="Use HTTP instead of HTTPS for the endpoint"
    )
    
    args = parser.parse_args()
    
    try:
        asyncio.run(async_main(args))
    except KeyboardInterrupt:
        print("\nBenchmark interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\nError: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
