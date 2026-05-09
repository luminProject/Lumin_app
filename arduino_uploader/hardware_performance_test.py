

"""
Hardware performance test for LUMIN real-time Arduino readings.

This script reads real values from an Arduino over USB Serial and sends them to:
POST /realtime-reading

It measures:
- Serial readings received from Arduino
- Successful backend requests
- Failed backend requests
- Average backend response time
- Minimum backend response time
- Maximum backend response time
- Requests per second

Expected Arduino serial format:
    voltage,current

Example:
    220.5,1.2

Usage on Windows:
    python arduino_uploader/hardware_performance_test.py --port COM11 --device-id 50 --requests 30

If your Arduino uses a different COM port:
    python arduino_uploader/hardware_performance_test.py --port COM5 --device-id 50 --requests 30
"""

from __future__ import annotations

import argparse
import statistics
import time
from datetime import datetime, timezone
from typing import Any

import requests
import serial


DEFAULT_BACKEND = "http://127.0.0.1:8000"
DEFAULT_ENDPOINT = "/realtime-reading"
DEFAULT_PORT = "COM11"
DEFAULT_BAUD_RATE = 9600
DEFAULT_REQUESTS = 30
DEFAULT_TIMEOUT_SECONDS = 10
DEFAULT_SERIAL_TIMEOUT_SECONDS = 3
DEFAULT_SCALE_FACTOR = 1.0


def parse_arduino_line(line: str) -> tuple[float, float] | None:
    """
    Parse Arduino serial line.

    Expected format:
        voltage,current

    Returns:
        (voltage, current) if valid, otherwise None.
    """
    parts = line.strip().split(",")
    if len(parts) != 2:
        return None

    try:
        voltage = float(parts[0].strip())
        current = float(parts[1].strip())
        return voltage, current
    except ValueError:
        return None


def calculate_watts(voltage: float, current: float, scale_factor: float) -> float:
    """Calculate watts from voltage and current."""
    return voltage * current * scale_factor


def build_payload(device_id: str, watts: float) -> dict[str, Any]:
    """Create backend payload for one Arduino reading."""
    return {
        "device_id": device_id,
        "watts": round(watts, 2),
        "reading_time": datetime.now(timezone.utc).isoformat(),
    }


def send_reading(
    url: str,
    device_id: str,
    watts: float,
    timeout: int,
) -> tuple[bool, float, int | None, str | None]:
    """
    Send one reading to the backend.

    Returns:
        success, response_time_seconds, status_code, error_message
    """
    payload = build_payload(device_id=device_id, watts=watts)
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


def run_hardware_performance_test(
    backend: str,
    port: str,
    baud_rate: int,
    device_id: str,
    requests_count: int,
    request_timeout: int,
    serial_timeout: int,
    scale_factor: float,
) -> None:
    """Read Arduino serial data and measure backend request performance."""
    url = backend.rstrip("/") + DEFAULT_ENDPOINT
    response_times: list[float] = []
    success_count = 0
    failure_count = 0
    invalid_serial_count = 0
    serial_read_count = 0
    failures: list[str] = []

    print("Starting LUMIN Arduino hardware performance test...")
    print(f"Serial port: {port}")
    print(f"Baud rate: {baud_rate}")
    print(f"Backend URL: {url}")
    print(f"Device ID: {device_id}")
    print(f"Target requests: {requests_count}")
    print("-" * 70)

    test_start = time.perf_counter()

    try:
        with serial.Serial(port, baud_rate, timeout=serial_timeout) as arduino:
            time.sleep(2)
            arduino.reset_input_buffer()

            while success_count + failure_count < requests_count:
                raw_line = arduino.readline().decode("utf-8", errors="ignore").strip()
                if not raw_line:
                    invalid_serial_count += 1
                    print("[SERIAL] Empty reading received; waiting for next line...")
                    continue

                parsed = parse_arduino_line(raw_line)
                if parsed is None:
                    invalid_serial_count += 1
                    print(f"[SERIAL] Invalid line skipped: {raw_line}")
                    continue

                serial_read_count += 1
                voltage, current = parsed
                watts = calculate_watts(voltage, current, scale_factor)

                request_number = success_count + failure_count + 1
                success, elapsed, status_code, error = send_reading(
                    url=url,
                    device_id=device_id,
                    watts=watts,
                    timeout=request_timeout,
                )

                response_times.append(elapsed)

                if success:
                    success_count += 1
                    print(
                        f"[{request_number:03}/{requests_count}] SUCCESS "
                        f"status={status_code} time={elapsed:.3f}s "
                        f"voltage={voltage:.2f} current={current:.3f} watts={watts:.2f}"
                    )
                else:
                    failure_count += 1
                    failure_message = (
                        f"[{request_number:03}/{requests_count}] FAILED "
                        f"status={status_code} time={elapsed:.3f}s error={error}"
                    )
                    failures.append(failure_message)
                    print(failure_message)

    except serial.SerialException as exc:
        print(f"Could not open serial port {port}: {exc}")
        print("Check that the Arduino is connected and the COM port is correct.")
        return
    except KeyboardInterrupt:
        print("\nTest stopped by user.")

    total_duration = time.perf_counter() - test_start
    average_time = statistics.mean(response_times) if response_times else 0.0
    min_time = min(response_times) if response_times else 0.0
    max_time = max(response_times) if response_times else 0.0
    total_requests = success_count + failure_count
    requests_per_second = total_requests / total_duration if total_duration > 0 else 0.0
    success_rate = (success_count / total_requests) * 100 if total_requests else 0.0

    print("\n" + "=" * 70)
    print("LUMIN Arduino Hardware Performance Test Summary")
    print("=" * 70)
    print(f"Serial readings parsed:   {serial_read_count}")
    print(f"Invalid serial readings:  {invalid_serial_count}")
    print(f"Total backend requests:   {total_requests}")
    print(f"Successful requests:      {success_count}")
    print(f"Failed requests:          {failure_count}")
    print(f"Success rate:             {success_rate:.2f}%")
    print(f"Total duration:           {total_duration:.3f} seconds")
    print(f"Average response:         {average_time:.3f} seconds")
    print(f"Minimum response:         {min_time:.3f} seconds")
    print(f"Maximum response:         {max_time:.3f} seconds")
    print(f"Requests per second:      {requests_per_second:.2f}")

    if failures:
        print("\nFailures:")
        for failure in failures[:10]:
            print(failure)
        if len(failures) > 10:
            print(f"...and {len(failures) - 10} more failures")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a hardware performance test for LUMIN Arduino readings."
    )
    parser.add_argument(
        "--backend",
        default=DEFAULT_BACKEND,
        help="Backend base URL. Default: http://127.0.0.1:8000",
    )
    parser.add_argument(
        "--port",
        default=DEFAULT_PORT,
        help="Arduino serial port. Default: COM11",
    )
    parser.add_argument(
        "--baud-rate",
        type=int,
        default=DEFAULT_BAUD_RATE,
        help="Arduino baud rate. Default: 9600",
    )
    parser.add_argument(
        "--device-id",
        required=True,
        help="Device ID from Supabase device table.",
    )
    parser.add_argument(
        "--requests",
        type=int,
        default=DEFAULT_REQUESTS,
        help="Number of backend requests to send. Default: 30",
    )
    parser.add_argument(
        "--request-timeout",
        type=int,
        default=DEFAULT_TIMEOUT_SECONDS,
        help="Backend request timeout in seconds. Default: 10",
    )
    parser.add_argument(
        "--serial-timeout",
        type=int,
        default=DEFAULT_SERIAL_TIMEOUT_SECONDS,
        help="Serial read timeout in seconds. Default: 3",
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=DEFAULT_SCALE_FACTOR,
        help="Optional scaling factor for watts. Default: 1.0",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    run_hardware_performance_test(
        backend=args.backend,
        port=args.port,
        baud_rate=args.baud_rate,
        device_id=args.device_id,
        requests_count=args.requests,
        request_timeout=args.request_timeout,
        serial_timeout=args.serial_timeout,
        scale_factor=args.scale_factor,
    )


if __name__ == "__main__":
    main()