#!/usr/bin/env python3
"""
ONNX to RKNN Model Conversion Script

Converts ONNX models to RKNN format optimized for RK3588 NPU.
Supports INT8 quantization with calibration dataset.

Usage:
    python scripts/convert_model.py --input model.onnx --output model.rknn --type detection
    python scripts/convert_model.py --input model.onnx --output model.rknn --quantize int8 --dataset ./cal_images/
"""

import argparse
import os
import sys
from pathlib import Path


def parse_args():
    parser = argparse.ArgumentParser(
        description="Convert ONNX model to RKNN format for RK3588 NPU"
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Input ONNX model path"
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Output RKNN model path"
    )
    parser.add_argument(
        "--type",
        "-t",
        choices=["detection", "segmentation", "pose", "classification", "face", "ocr"],
        default="detection",
        help="Model type (default: detection)",
    )
    parser.add_argument(
        "--quantize",
        "-q",
        choices=["fp16", "int8", "dynamic"],
        default="int8",
        help="Quantization type (default: int8)",
    )
    parser.add_argument(
        "--dataset",
        "-d",
        help="Calibration dataset directory (required for int8)",
    )
    parser.add_argument(
        "--input-size",
        nargs=2,
        type=int,
        default=[640, 640],
        metavar=("W", "H"),
        help="Model input size (default: 640 640)",
    )
    parser.add_argument(
        "--mean",
        nargs=3,
        type=float,
        default=[0, 0, 0],
        help="Input mean values (default: 0 0 0)",
    )
    parser.add_argument(
        "--std",
        nargs=3,
        type=float,
        default=[255, 255, 255],
        help="Input std values (default: 255 255 255)",
    )
    parser.add_argument(
        "--target-platform",
        default="rk3588",
        help="Target platform (default: rk3588)",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    return parser.parse_args()


def get_calibration_images(dataset_dir: str, input_size: tuple, max_images: int = 50):
    """Load calibration images for INT8 quantization."""
    import cv2
    import numpy as np

    images = []
    dataset_path = Path(dataset_dir)
    extensions = {".jpg", ".jpeg", ".png", ".bmp"}

    for img_file in sorted(dataset_path.iterdir()):
        if img_file.suffix.lower() not in extensions:
            continue
        if len(images) >= max_images:
            break

        img = cv2.imread(str(img_file))
        if img is None:
            continue

        img = cv2.resize(img, input_size)
        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        images.append(img)

    print(f"Loaded {len(images)} calibration images from {dataset_dir}")
    return images


def convert_model(args):
    """Convert ONNX model to RKNN format."""
    try:
        from rknn.api import RKNN
    except ImportError:
        print("ERROR: rknn-toolkit2 not installed.")
        print("Install it from: https://github.com/rockchip-linux/rknn-toolkit2")
        print()
        print("On x86 development machine:")
        print("  pip install rknn-toolkit2")
        print()
        print("On Orange Pi 5 (ARM):")
        print("  pip install rknn-toolkit2-lite")
        sys.exit(1)

    rknn = RKNN(verbose=args.verbose)

    # Configure
    print(f"[1/5] Configuring for {args.target_platform}...")
    rknn.config(
        mean_values=[args.mean],
        std_values=[args.std],
        target_platform=args.target_platform,
        quantized_dtype="asymmetric_quantized-8" if args.quantize == "int8" else "float16",
        quantized_algorithm="normal",
    )

    # Load ONNX
    print(f"[2/5] Loading ONNX model: {args.input}")
    ret = rknn.load_onnx(model=args.input)
    if ret != 0:
        print(f"ERROR: Failed to load ONNX model (code={ret})")
        sys.exit(1)

    # Build
    print(f"[3/5] Building RKNN model (quantize={args.quantize})...")
    do_quantize = args.quantize == "int8"
    dataset_path = args.dataset if do_quantize else None

    if do_quantize and dataset_path:
        # Create calibration dataset file
        dataset_file = "/tmp/rknn_calibration.txt"
        dataset_dir = Path(dataset_path)
        extensions = {".jpg", ".jpeg", ".png", ".bmp"}
        with open(dataset_file, "w") as f:
            for img in sorted(dataset_dir.iterdir()):
                if img.suffix.lower() in extensions:
                    f.write(str(img.absolute()) + "\n")
        dataset_path = dataset_file

    ret = rknn.build(
        do_quantization=do_quantize,
        dataset=dataset_path,
    )
    if ret != 0:
        print(f"ERROR: Failed to build model (code={ret})")
        sys.exit(1)

    # Export
    print(f"[4/5] Exporting to: {args.output}")
    ret = rknn.export_rknn(args.output)
    if ret != 0:
        print(f"ERROR: Failed to export RKNN model (code={ret})")
        sys.exit(1)

    # Summary
    file_size = os.path.getsize(args.output) / (1024 * 1024)
    print(f"[5/5] Conversion complete!")
    print(f"  Output: {args.output}")
    print(f"  Size: {file_size:.2f} MB")
    print(f"  Quantization: {args.quantize}")
    print(f"  Target: {args.target_platform}")

    rknn.release()


if __name__ == "__main__":
    args = parse_args()

    if not os.path.exists(args.input):
        print(f"ERROR: Input file not found: {args.input}")
        sys.exit(1)

    if args.quantize == "int8" and not args.dataset:
        print("WARNING: INT8 quantization without calibration dataset may reduce accuracy.")
        print("Consider providing --dataset path with representative images.")

    convert_model(args)
