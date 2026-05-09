

"""
Performance test for LUMIN real-time device readings.

This script tests the backend performance by sending simulated sensor readings to:
POST /realtime-reading

It measures:
- Total requests
- Successful requests
- Failed requests
- Average response time
- Minimum response time
- Maximum response time
- Requests per second

Usage:
    python arduino_uploader/performance_test.py

Optional:
    python arduino_uploader/performance_test.py --requests 30 --interval 0.2
    python arduino_uploader/performance_test.py --backend http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import random
import statistics
import time
from datetime import datetime, timezone
from typing import Any

import requests


DEFAULT_BACKEND = "http://127.0.0.1:8000"
DEFAULT_ENDPOINT = "/realtime-reading"
DEFAULT_REQUESTS = 30
DEFAULT_INTERVAL_SECONDS = 0.2
DEFAULT_TIMEOUT_SECONDS = 10

# Replace these with real device IDs from your Supabase device table if needed.
# These can be consumption or production devices.
DEFAULT_DEVICE_IDS = [
    "REPLACE_WITH_DEVICE_ID_1",
    "REPLACE_WITH_DEVICE_ID_2",
]


def build_payload(device_id: str) -> dict[str, Any]:
    """Create one simulated reading payload."""
    return {
        "device_id": device_id,
        "watts": round(random.uniform(50, 1200), 2),
        "reading_time": datetime.now(timezone.utc).isoformat(),
    }


def send_reading(
    url: str,
    device_id: str,
    timeout: int,
) -> tuple[bool, float, int | None, str | None]:
    """
    Send one reading and return:
    success, response_time_seconds, status_code, error_message
    """
    payload = build_payload(device_id)
    start = time.perf_counter()

    try:
        response = requests.post(url, json=payload, timeout=timeout)
        elapsed = time.perf_counter() - start
        success = 200 <= response.status_code < 300
        error_message = None if success else response.text[:200]
        return success, elapsed, response.status_code, error_message
    except requests.RequestException as exc:
        elapsed = time.perf_counter() - start
        return False, elapsed, None, str(exc)


def run_performance_test(
    backend: str,
    requests_count: int,
    interval_seconds: float,
    timeout_seconds: int,
    device_ids: list[str],
) -> None:
    """Run the simulator performance test and print a summary."""
    if not device_ids or any(device_id.startswith("REPLACE_WITH") for device_id in device_ids):
        raise ValueError(
            "Please replace DEFAULT_DEVICE_IDS with real device IDs from Supabase, "
            "or pass them using --device-id."
        )

    url = backend.rstrip("/") + DEFAULT_ENDPOINT
    response_times: list[float] = []
    success_count = 0
    failure_count = 0
    failures: list[str] = []

    print("Starting LUMIN realtime performance test...")
    print(f"Backend URL: {url}")
    print(f"Total requests: {requests_count}")
    print(f"Interval: {interval_seconds} seconds")
    print("-" * 60)

    test_start = time.perf_counter()

    for index in range(1, requests_count + 1):
        device_id = device_ids[(index - 1) % len(device_ids)]
        success, elapsed, status_code, error = send_reading(
            url=url,
            device_id=device_id,
            timeout=timeout_seconds,
        )

        response_times.append(elapsed)

        if success:
            success_count += 1
            print(
                f"[{index:03}/{requests_count}] SUCCESS "
                f"status={status_code} time={elapsed:.3f}s device={device_id}"
            )
        else:
            failure_count += 1
            failure_message = (
                f"[{index:03}/{requests_count}] FAILED "
                f"status={status_code} time={elapsed:.3f}s error={error}"
            )
            failures.append(failure_message)
            print(failure_message)

        if index < requests_count:
            time.sleep(interval_seconds)

    total_duration = time.perf_counter() - test_start
    average_time = statistics.mean(response_times) if response_times else 0.0
    min_time = min(response_times) if response_times else 0.0
    max_time = max(response_times) if response_times else 0.0
    requests_per_second = requests_count / total_duration if total_duration > 0 else 0.0
    success_rate = (success_count / requests_count) * 100 if requests_count else 0.0

    print("\n" + "=" * 60)
    print("LUMIN Realtime Performance Test Summary")
    print("=" * 60)
    print(f"Total requests:       {requests_count}")
    print(f"Successful requests:  {success_count}")
    print(f"Failed requests:      {failure_count}")
    print(f"Success rate:         {success_rate:.2f}%")
    print(f"Total duration:       {total_duration:.3f} seconds")
    print(f"Average response:     {average_time:.3f} seconds")
    print(f"Minimum response:     {min_time:.3f} seconds")
    print(f"Maximum response:     {max_time:.3f} seconds")
    print(f"Requests per second:  {requests_per_second:.2f}")

    if failures:
        print("\nFailures:")
        for failure in failures[:10]:
            print(failure)
        if len(failures) > 10:
            print(f"...and {len(failures) - 10} more failures")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a performance test for LUMIN realtime readings."
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help="Backend base URL. Default: http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=DEFAULT_REQUESTS,
        help="Number of readings to send. Default: 30",
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=DEFAULT_INTERVAL_SECONDS,
        help="Delay between requests in seconds. Default: 0.2",
    )
    parser.add_argument(
        "--timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Request timeout in seconds. Default: 10",
    )
    parser.add_argument(
        "--device-id",
        action="append",
        dest="device_ids",
        help="Device ID to test. Can be passed multiple times.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    device_ids = args.device_ids if args.device_ids else DEFAULT_DEVICE_IDS

    run_performance_test(
        backend=args.backend,
        requests_count=args.requests,
        interval_seconds=args.interval,
        timeout_seconds=args.timeout,
        device_ids=device_ids,
    )


if __name__ == "__main__":
    main()