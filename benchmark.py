import httpx
import time
import statistics
import ssl
import traceback
import asyncio
from typing import Dict, List, Any, Optional, Tuple

import random
import string

DEFAULT_REQUEST_DELAY = 2.0

async def make_request(
    client: httpx.AsyncClient,
    endpoint: str,
    api_key: str,
    model: str,
    prompt: str,
    timeout: float,
    debug: bool = False,
) -> Tuple[float, Optional[Dict[str, Any]], Optional[Exception]]:
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
    debug: bool = False,
    randomize_prompt: bool = False,
) -> List[float]:
    response_times = []
    successful_requests = 0

    try_http = False
    verify_ssl = False

    # try_http is always False, so this block will never execute

    async with httpx.AsyncClient(verify=verify_ssl) as client:
        for i in range(num_requests):
            retry_count = 0
            # Randomize prompt if requested
            if randomize_prompt:
                rand_suffix = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                prompt_to_use = f"{prompt} [rnd:{rand_suffix}]"
            else:
                prompt_to_use = prompt
            while retry_count <= max_retries:
                try_endpoint = endpoint
                response_time, response_data, exception = await make_request(
                    client, try_endpoint, api_key, model, prompt_to_use, timeout, debug
                )
                # If HTTPS fails with SSL error and debug is enabled, try HTTP
                if response_data is None and debug and endpoint.startswith("https://"):
                    if exception and (isinstance(exception, (ssl.SSLError, httpx.SSLError)) or "SSL" in str(exception) or "TLS" in str(exception)):
                        http_endpoint = endpoint.replace("https://", "http://")
                        print(f"\nDebug: HTTPS failed with SSL error, trying HTTP: {http_endpoint}")
                        response_time, response_data, http_exception = await make_request(
                            client, http_endpoint, api_key, model, prompt_to_use, timeout, debug
                        )
                if response_data is not None:
                    response_times.append(response_time)
                    successful_requests += 1
                    break
                else:
                    retry_count += 1
                    if retry_count <= max_retries:
                        await asyncio.sleep(retry_delay * retry_count)
                    else:
                        break
            if i < num_requests - 1:
                await asyncio.sleep(request_delay)
    return response_times

def calculate_statistics(response_times: List[float]) -> Dict[str, float]:
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

def generate_ascii_histogram(response_times: List[float], bins: int = 10) -> str:
    if not response_times:
        return "No data to display"
    min_time = min(response_times)
    max_time = max(response_times)
    if min_time == max_time:
        bin_width = 0.1
    else:
        bin_width = (max_time - min_time) / bins
    bin_counts = [0] * bins
    for time_val in response_times:
        bin_index = min(bins - 1, int((time_val - min_time) / bin_width))
        bin_counts[bin_index] += 1
    max_count = max(bin_counts) if bin_counts else 0
    scale_factor = 40 / max_count if max_count > 0 else 1
    histogram = []
    for i, count in enumerate(bin_counts):
        bin_start = min_time + i * bin_width
        bin_end = bin_start + bin_width
        bar = "#" * int(count * scale_factor)
        histogram.append(f"{bin_start:.4f} - {bin_end:.4f} | {bar} ({count})")
    return "\n".join(histogram)