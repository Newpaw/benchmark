from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from pydantic import BaseModel, Field
from typing import Optional
import secrets
import os
import asyncio

from benchmark import run_benchmark, calculate_statistics, generate_ascii_histogram

router = APIRouter()
security = HTTPBasic()

# For demo: hardcoded username/password, or use env vars
API_USERNAME = os.environ.get("BENCHMARK_API_USER", "admin")
API_PASSWORD = os.environ.get("BENCHMARK_API_PASS", "password")

def verify_basic_auth(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, API_USERNAME)
    correct_password = secrets.compare_digest(credentials.password, API_PASSWORD)
    if not (correct_username and correct_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Basic"},
        )
    return credentials.username

class BenchmarkRequest(BaseModel):
    """
    Request model for the /benchmark endpoint.

    Fields:
        endpoint (str): The target API endpoint to benchmark.
        api_key (str): API key for authentication with the target endpoint.
        model (str): Model identifier to use for the benchmark.
        prompt (str): Prompt to send to the model.
        num_requests (int): Number of requests to send (1-1000, default: 10).

    Example:
        {
            "endpoint": "http://litellm.ai-sandbox.azure.to2cz.cz",
            "api_key": "sk-...",
            "model": "gpt-3.5-turbo",
            "prompt": "Hello, world!",
            "num_requests": 10
        }
    """
    endpoint: str = "http://litellm.ai-sandbox.azure.to2cz.cz"
    api_key: str
    model: str
    prompt: str
    num_requests: int = Field(10, ge=1, le=1000)

class StatsModel(BaseModel):
    """
    Schema for benchmark statistics.

    Fields:
        count (int): Number of requests.
        min (float): Minimum response time.
        max (float): Maximum response time.
        mean (float): Mean response time.
        median (float): Median response time.
        stdev (float): Standard deviation of response times.
        p90 (float): 90th percentile response time.
        p95 (float): 95th percentile response time.
        p99 (float): 99th percentile response time.

    Example:
        {
            "count": 10,
            "min": 0.42,
            "max": 0.98,
            "mean": 0.65,
            "median": 0.63,
            "stdev": 0.18,
            "p90": 0.92,
            "p95": 0.98,
            "p99": 0.98
        }
    """
    count: int
    min: float
    max: float
    mean: float
    median: float
    stdev: float
    p90: float
    p95: float
    p99: float

class BenchmarkResponse(BaseModel):
    """
    Response model for the /benchmark endpoint.

    Fields:
        stats (StatsModel): Benchmark statistics, including count, min, max, mean, median, stdev, p90, p95, p99.
        histogram (str): ASCII histogram of response times, formatted as multiple lines, each representing a response time bucket and the number of responses in that bucket using asterisks.

    Example:
        {
            "stats": {
                "count": 10,
                "min": 0.42,
                "max": 0.98,
                "mean": 0.65,
                "median": 0.63,
                "stdev": 0.18,
                "p90": 0.92,
                "p95": 0.98,
                "p99": 0.98
            },
            "histogram": "0.4-0.5: **\\n0.5-0.6: ***\\n0.6-0.7: ***\\n0.7-0.8: *\\n0.8-0.9: *\\n0.9-1.0: *"
        }

    Histogram format:
        Each line represents a bucket of response times, e.g.:
            "0.4-0.5: **"
            "0.5-0.6: ***"
        where the range is the response time interval and the asterisks represent the count of responses in that interval.
    """
    stats: StatsModel
    histogram: str

class ErrorResponse(BaseModel):
    """
    Error response model.

    Fields:
        detail (str): Error message.

    Example:
        {
            "detail": "Incorrect username or password"
        }
    """
    detail: str

@router.post(
    "/benchmark",
    response_model=BenchmarkResponse,
    responses={
        200: {
            "description": "Benchmark statistics and ASCII histogram.",
            "content": {
                "application/json": {
                    "example": {
                        "stats": {
                            "count": 10,
                            "min": 0.42,
                            "max": 0.98,
                            "mean": 0.65,
                            "median": 0.63,
                            "stdev": 0.18,
                            "p90": 0.92,
                            "p95": 0.98,
                            "p99": 0.98
                        },
                        "histogram": "0.4-0.5: **\\n0.5-0.6: ***\\n0.6-0.7: ***\\n0.7-0.8: *\\n0.8-0.9: *\\n0.9-1.0: *"
                    }
                }
            }
        },
        401: {
            "model": ErrorResponse,
            "description": "Unauthorized. Authentication failed.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Incorrect username or password"
                    }
                }
            }
        },
        422: {
            "description": "Validation error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": [
                            {
                                "loc": ["body", "api_key"],
                                "msg": "field required",
                                "type": "value_error.missing"
                            }
                        ]
                    }
                }
            }
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error.",
            "content": {
                "application/json": {
                    "example": {
                        "detail": "Internal server error"
                    }
                }
            }
        }
    }
)
async def benchmark_api(
    params: BenchmarkRequest,
    timeout: float = 30.0,
    max_retries: int = 3,
    retry_delay: float = 1.0,
    request_delay: float = 2.0,
    debug: bool = False,
    randomize_prompt: bool = False,
    username: str = Depends(verify_basic_auth)
):
    """
    Run a benchmark against a specified model API endpoint.

    Returns benchmark statistics and an ASCII histogram of response times.

    Successful Response (HTTP 200):
        - Content-Type: application/json
        - Body: BenchmarkResponse (see example below)

    Example Successful Response:
        {
            "stats": {
                "count": 10,
                "min": 0.42,
                "max": 0.98,
                "mean": 0.65,
                "median": 0.63,
                "stdev": 0.18,
                "p90": 0.92,
                "p95": 0.98,
                "p99": 0.98
            },
            "histogram": "0.4-0.5: **\\n0.5-0.6: ***\\n0.6-0.7: ***\\n0.7-0.8: *\\n0.8-0.9: *\\n0.9-1.0: *"
        }

    Histogram format:
        Each line represents a bucket of response times, e.g.:
            "0.4-0.5: **"
            "0.5-0.6: ***"
        where the range is the response time interval and the asterisks represent the count of responses in that interval.

    Error Responses:
        - 401 Unauthorized: If authentication fails.
            Example:
                {
                    "detail": "Incorrect username or password"
                }
        - 422 Unprocessable Entity: If the request payload is invalid.
            Example:
                {
                    "detail": [
                        {
                            "loc": ["body", "api_key"],
                            "msg": "field required",
                            "type": "value_error.missing"
                        }
                    ]
                }
        - 500 Internal Server Error: If an unexpected error occurs.
            Example:
                {
                    "detail": "Internal server error"
                }

    Error Handling Guidance:
        - For 401 errors, check your authentication credentials.
        - For 422 errors, verify your request payload matches the expected schema.
        - For 500 errors, retry later or contact the service administrator.

    """
    response_times = await run_benchmark(
        endpoint=params.endpoint,
        api_key=params.api_key,
        model=params.model,
        prompt=params.prompt,
        num_requests=params.num_requests,
        timeout=timeout,
        max_retries=max_retries,
        retry_delay=retry_delay,
        request_delay=request_delay,
        debug=debug,
        randomize_prompt=randomize_prompt,
    )
    stats = calculate_statistics(response_times)
    histogram = generate_ascii_histogram(response_times)
    return BenchmarkResponse(stats=StatsModel(**stats), histogram=histogram)