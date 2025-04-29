# LLM Benchmark Tool

A minimalist Python tool to benchmark Language Model (LLM) performance metrics, focusing on latency and statistical analysis. This project provides both a command-line interface and a FastAPI-based REST API to benchmark OpenAI-compatible endpoints, measuring response times and providing detailed statistics.

## Features

- Measures latency (response time) with detailed statistical analysis
- Provides mean, median, standard deviation, and percentile metrics
- Visualizes results with ASCII histograms in the console
- Implements robust error handling and retry logic
- Configurable parameters for endpoint, API key, model, etc.
- Exposes a REST API for programmatic benchmarking

## Requirements

- Python 3.11 or higher

### Dependencies

- fastapi
- httpx
- python-dotenv
- python-multipart
- uvicorn

All dependencies are specified in [pyproject.toml](pyproject.toml).

## Installation

1. Clone this repository:
   ```
   git clone <repository-url>
   cd benchmark
   ```

2. Install dependencies using [uv](https://github.com/astral-sh/uv):
   ```
   uv pip install -e .
   ```

## Usage

### Command-Line Interface

Run the benchmark with default settings:

```bash
python main.py
```

#### Command Line Options

The script supports various command line options to customize the benchmark:

```
usage: main.py [-h] [--endpoint ENDPOINT] [--api-key API_KEY] [--model MODEL]
               [--prompt PROMPT] [--num-requests NUM_REQUESTS]
               [--timeout TIMEOUT] [--max-retries MAX_RETRIES]
               [--retry-delay RETRY_DELAY]

Benchmark an LLM API for latency performance

options:
  -h, --help            show this help message and exit
  --endpoint ENDPOINT   API endpoint URL (default: http://litellm.ai-sandbox.azure.to2cz.cz)
  --api-key API_KEY     API key for authentication
  --no-verify-ssl       Disable SSL certificate verification
  --debug               Enable debug mode with additional logging
  --try-http            Use HTTP instead of HTTPS for the endpoint
  --request-delay DELAY Delay between requests in seconds to avoid rate limiting (default: 2.0)
  --model MODEL         Model to use (default: gpt-4o)
  --prompt PROMPT       Prompt to send (default: 'Tell me a short joke')
  --num-requests NUM_REQUESTS
                        Number of requests to make (default: 10)
  --timeout TIMEOUT     Request timeout in seconds (default: 30.0)
  --max-retries MAX_RETRIES
                        Maximum number of retries for failed requests (default: 3)
  --retry-delay RETRY_DELAY
                        Base delay between retries in seconds (default: 1.0)
```

#### Examples

Run with a custom endpoint and API key:

```bash
python main.py --endpoint "https://api.example.com" --api-key "your-api-key"
```

Run with a different model and prompt:

```bash
python main.py --model "gpt-4" --prompt "Explain quantum computing in one sentence"
```

Increase the number of requests and timeout:

```bash
python main.py --num-requests 20 --timeout 60
```

Run with increased delay between requests to avoid rate limiting:

```bash
python main.py --request-delay 5.0
```

### REST API

You can also run the FastAPI server to access the benchmarking functionality via HTTP endpoints.

#### Start the API server

```bash
uvicorn main:app --reload
```

#### Example API Usage

- **POST /benchmark**

  Send a POST request to `/benchmark` with a JSON payload specifying the endpoint, API key, prompt, and other parameters.

  Example request:

  ```bash
  curl -X POST "http://localhost:8000/benchmark" \
    -H "Content-Type: application/json" \
    -d '{
      "endpoint": "https://api.example.com",
      "api_key": "your-api-key",
      "model": "gpt-4",
      "prompt": "Tell me a short joke",
      "num_requests": 10
    }'
  ```

  The response will include latency statistics and an ASCII histogram.

## Output

The benchmark will output:

1. Progress of each request with response time
2. Statistical summary of latency metrics
3. ASCII histogram showing the distribution of response times

Example output:

```
Starting benchmark with 10 requests to https://litellm.ai-sandbox.azure.to2cz.cz
Model: gpt-4o
Prompt: 'Tell me a short joke'
--------------------------------------------------
Request 1/10 - 0.8765s
Request 2/10 - 0.7654s
Request 3/10 - 0.9876s
...
--------------------------------------------------
Completed 10/10 requests successfully

Benchmark Results:
--------------------------------------------------
Total requests: 10
Min latency: 0.7654s
Max latency: 1.2345s
Mean latency: 0.9876s
Median latency: 0.9543s
Standard deviation: 0.1234s
90th percentile: 1.1234s
95th percentile: 1.1987s
99th percentile: 1.2345s

Latency Distribution:
--------------------------------------------------
0.7654 - 0.8123 | ##### (2)
0.8123 - 0.8592 | ## (1)
...
```

## Troubleshooting

### SSL Issues

If you encounter SSL errors like `[SSL: WRONG_VERSION_NUMBER] wrong version number`, it typically means there's a protocol mismatch between the client and server. Try these solutions:

1. Use HTTP instead of HTTPS:
   ```bash
   python main.py --try-http
   ```

2. Disable SSL verification (not recommended for production):
   ```bash
   python main.py --no-verify-ssl
   ```

3. Enable debug mode for more detailed error information:
   ```bash
   python main.py --debug
   ```

## Error Handling

The tool implements robust error handling:

- Connection errors: Retry with exponential backoff
- Authentication errors: Clear error message with verification steps
- Rate limiting: Implement backoff and retry with configurable delays between requests
- Timeout handling: Set appropriate timeouts and handle gracefully
- General exceptions: Catch and provide meaningful error messages

## For Developers & Contributors

- **Project Structure:**
  - `main.py`: FastAPI app entry point.
  - `api.py`: API routes and request/response models.
  - `benchmark.py`: Core benchmarking logic, statistics, and visualization.
  - `benchmark_plan.md`: Project plan and architecture overview.
  - `pyproject.toml`: Project metadata and dependencies.

- **Development Server:**
  - Run `uvicorn main:app --reload` for local development.
  - API documentation available at `http://localhost:8000/docs`.

- **Testing:**
  - Ensure you have Python 3.11+ and all dependencies installed.
  - Use the CLI or REST API to test benchmarking functionality.

- **Contributing:**
  - Please follow standard Python best practices.
  - Add tests for new features or bug fixes.
  - Document any changes in the code and update this README as needed.

## License

[MIT License](LICENSE)