#!/usr/bin/env python3
"""
Model Benchmark Script

Measures inference performance of RKNN models on Orange Pi 5 NPU.
Reports latency statistics (avg, min, max, p50, p95, p99) and throughput.

Usage:
    python scripts/benchmark.py --model models/detection/yolov8n.rknn
    python scripts/benchmark.py --model models/detection/yolov8n.rknn --iterations 200 --warmup 20
"""

import argparse
import os
import sys
import time
from pathlib import Path

import numpy as np


def parse_args():
    parser = argparse.ArgumentParser(description="Benchmark RKNN model inference performance")
    parser.add_argument("--model", "-m", required=True, help="RKNN model file path")
    parser.add_argument(
        "--input-size",
        nargs=2,
        type=int,
        default=[640, 640],
        metavar=("W", "H"),
        help="Input size (default: 640 640)",
    )
    parser.add_argument(
        "--iterations", "-n", type=int, default=100, help="Number of iterations (default: 100)"
    )
    parser.add_argument(
        "--warmup", "-w", type=int, default=10, help="Warmup iterations (default: 10)"
    )
    parser.add_argument(
        "--core-mask",
        type=int,
        default=7,
        choices=[1, 2, 4, 3, 5, 6, 7],
        help="NPU core mask (default: 7 = all cores)",
    )
    parser.add_argument("--verbose", "-v", action="store_true")
    return parser.parse_args()


def run_benchmark(args):
    """Run benchmark on RKNN model."""
    model_path = args.model
    w, h = args.input_size
    n_iter = args.iterations
    n_warmup = args.warmup

    print("=" * 60)
    print("RKNN Model Benchmark")
    print("=" * 60)
    print(f"Model:      {model_path}")
    print(f"Input size: {w}x{h}")
    print(f"Iterations: {n_iter} (warmup: {n_warmup})")
    print(f"Core mask:  {args.core_mask}")
    print("-" * 60)

    # Try RKNN Lite (on device) first, then RKNN (development)
    try:
        from rknnlite.api import RKNNLite as RKNN

        rknn = RKNN()
        print("Using: RKNN Lite (on-device)")
    except ImportError:
        try:
            from rknn.api import RKNN

            rknn = RKNN()
            print("Using: RKNN Toolkit2 (development)")
        except ImportError:
            print("ERROR: Neither rknnlite nor rknn-toolkit2 is installed.")
            print()
            print("Running mock benchmark with random data...")
            _run_mock_benchmark(w, h, n_iter, n_warmup)
            return

    # Load model
    print("Loading model...")
    ret = rknn.load_rknn(model_path)
    if ret != 0:
        print(f"ERROR: Failed to load model (code={ret})")
        sys.exit(1)

    ret = rknn.init_runtime(core_mask=args.core_mask)
    if ret != 0:
        print(f"ERROR: Failed to init runtime (code={ret})")
        sys.exit(1)

    # Create dummy input
    dummy_input = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)

    # Warmup
    print(f"Warming up ({n_warmup} iterations)...")
    for _ in range(n_warmup):
        rknn.inference(inputs=[dummy_input])

    # Benchmark
    print(f"Benchmarking ({n_iter} iterations)...")
    times = []
    for i in range(n_iter):
        start = time.perf_counter()
        rknn.inference(inputs=[dummy_input])
        elapsed = (time.perf_counter() - start) * 1000  # ms
        times.append(elapsed)
        if args.verbose and (i + 1) % 10 == 0:
            print(f"  [{i+1}/{n_iter}] {elapsed:.2f}ms")

    rknn.release()

    # Print results
    _print_results(times, model_path, w, h, args.core_mask)


def _run_mock_benchmark(w, h, n_iter, n_warmup):
    """Mock benchmark for testing without NPU hardware."""
    import time

    dummy_input = np.random.randint(0, 255, (h, w, 3), dtype=np.uint8)
    times = []

    for _ in range(n_warmup):
        _ = np.sum(dummy_input)

    for _ in range(n_iter):
        start = time.perf_counter()
        _ = np.sum(dummy_input)
        time.sleep(0.03)  # Simulate ~30ms inference
        elapsed = (time.perf_counter() - start) * 1000
        times.append(elapsed)

    _print_results(times, "mock_model", w, h, 7)


def _print_results(times, model_path, w, h, core_mask):
    """Print benchmark results."""
    times = np.array(times)
    n = len(times)

    print()
    print("=" * 60)
    print("Results")
    print("=" * 60)
    print(f"Model:          {Path(model_path).name}")
    print(f"Input:          {w}x{h}")
    print(f"Core mask:      {core_mask}")
    print(f"Iterations:     {n}")
    print("-" * 60)
    print(f"Mean:           {np.mean(times):.2f} ms")
    print(f"Std:            {np.std(times):.2f} ms")
    print(f"Min:            {np.min(times):.2f} ms")
    print(f"Max:            {np.max(times):.2f} ms")
    print(f"Median (P50):   {np.percentile(times, 50):.2f} ms")
    print(f"P95:            {np.percentile(times, 95):.2f} ms")
    print(f"P99:            {np.percentile(times, 99):.2f} ms")
    print("-" * 60)
    print(f"Throughput:     {1000 / np.mean(times):.1f} FPS")
    print("=" * 60)


if __name__ == "__main__":
    args = parse_args()

    if not os.path.exists(args.model):
        print(f"ERROR: Model file not found: {args.model}")
        sys.exit(1)

    run_benchmark(args)
