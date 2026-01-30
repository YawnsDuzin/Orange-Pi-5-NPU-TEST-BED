"""
System Monitor Module

Monitors hardware resources: CPU, NPU, memory, temperature, and disk.
Optimized for Orange Pi 5 Plus (RK3588) with sysfs-based readings.
Falls back to cross-platform methods on Windows/macOS.
"""

import asyncio
import logging
import os
import platform
import shutil
import socket
import time
from pathlib import Path
from typing import Optional

from app.models.system import (
    CPUInfo,
    DiskInfo,
    MemoryInfo,
    NetworkInfo,
    NPUInfo,
    SystemStatus,
    TemperatureInfo,
)

logger = logging.getLogger(__name__)

IS_LINUX = platform.system() == "Linux"
IS_WINDOWS = platform.system() == "Windows"


class SystemMonitor:
    """
    System Monitor - periodic hardware status polling.

    Reads hardware metrics from /proc and /sys on Linux.
    Falls back to cross-platform methods (psutil / shutil / socket)
    on Windows and macOS.
    Designed for Orange Pi 5 Plus (RK3588) but degrades gracefully
    on other platforms.
    """

    def __init__(self, poll_interval: float = 2.0):
        self._poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._status = SystemStatus()
        self._start_time = time.monotonic()

        # For CPU usage delta calculation (Linux /proc/stat)
        self._prev_cpu_times: Optional[list[int]] = None

        # Optional psutil (cross-platform fallback)
        self._psutil = None
        if not IS_LINUX:
            try:
                import psutil
                self._psutil = psutil
            except ImportError:
                logger.warning(
                    "psutil not installed - system metrics will be limited on %s. "
                    "Install with: pip install psutil",
                    platform.system(),
                )

    @property
    def status(self) -> SystemStatus:
        """Get latest system status."""
        return self._status

    async def start(self) -> None:
        """Start periodic monitoring."""
        if self._running:
            return
        self._running = True
        self._start_time = time.monotonic()
        self._task = asyncio.create_task(self._monitor_loop())
        logger.info("System monitor started")

    async def stop(self) -> None:
        """Stop monitoring."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("System monitor stopped")

    async def get_status(self) -> SystemStatus:
        """Get current system status (with fresh read)."""
        loop = asyncio.get_running_loop()
        status = await loop.run_in_executor(None, self._read_all_metrics)
        self._status = status
        return status

    async def _monitor_loop(self) -> None:
        """Periodic monitoring loop."""
        loop = asyncio.get_running_loop()
        while self._running:
            try:
                self._status = await loop.run_in_executor(None, self._read_all_metrics)
            except Exception as e:
                logger.error(f"System monitor error: {e}")
            await asyncio.sleep(self._poll_interval)

    def _read_all_metrics(self) -> SystemStatus:
        """Read all hardware metrics (synchronous, for thread pool)."""
        return SystemStatus(
            cpu=self._read_cpu(),
            npu=self._read_npu(),
            memory=self._read_memory(),
            temperature=self._read_temperature(),
            disk=self._read_disk(),
            network=self._read_network(),
            uptime_seconds=time.monotonic() - self._start_time,
        )

    def _read_cpu(self) -> CPUInfo:
        """Read CPU usage from /proc/stat (Linux) or psutil (cross-platform)."""
        info = CPUInfo()
        try:
            if IS_LINUX:
                self._read_cpu_linux(info)
            elif self._psutil:
                self._read_cpu_psutil(info)
            else:
                info.core_count = os.cpu_count() or 0
        except Exception as e:
            logger.debug(f"CPU read error: {e}")
        return info

    def _read_cpu_linux(self, info: CPUInfo) -> None:
        """Read CPU via /proc/stat (Linux only)."""
        with open("/proc/stat") as f:
            lines = f.readlines()

        parts = lines[0].split()
        if parts[0] == "cpu":
            times = [int(x) for x in parts[1:]]
            total = sum(times)
            idle = times[3] + (times[4] if len(times) > 4 else 0)

            if self._prev_cpu_times is not None:
                prev_total = sum(self._prev_cpu_times)
                prev_idle = self._prev_cpu_times[3] + (
                    self._prev_cpu_times[4] if len(self._prev_cpu_times) > 4 else 0
                )
                delta_total = total - prev_total
                delta_idle = idle - prev_idle
                if delta_total > 0:
                    info.usage_percent = round(
                        (1 - delta_idle / delta_total) * 100, 1
                    )

            self._prev_cpu_times = times

        info.core_count = sum(1 for l in lines if l.startswith("cpu") and l[3:4].isdigit())

        freq_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
        if os.path.exists(freq_path):
            with open(freq_path) as f:
                info.frequency_mhz = round(int(f.read().strip()) / 1000, 0)

        per_core = []
        for line in lines[1:]:
            if line.startswith("cpu") and line[3:4].isdigit():
                core_parts = line.split()
                core_times = [int(x) for x in core_parts[1:]]
                core_total = sum(core_times)
                core_idle = core_times[3] + (core_times[4] if len(core_times) > 4 else 0)
                if core_total > 0:
                    per_core.append(round((1 - core_idle / core_total) * 100, 1))
        info.per_core_usage = per_core

    def _read_cpu_psutil(self, info: CPUInfo) -> None:
        """Read CPU via psutil (cross-platform)."""
        ps = self._psutil
        info.usage_percent = ps.cpu_percent(interval=0)
        info.core_count = ps.cpu_count(logical=True) or 0
        freq = ps.cpu_freq()
        if freq:
            info.frequency_mhz = round(freq.current, 0)
        per_core = ps.cpu_percent(interval=0, percpu=True)
        if per_core:
            info.per_core_usage = [round(v, 1) for v in per_core]

    def _read_npu(self) -> NPUInfo:
        """Read NPU status from sysfs (Linux/RK3588 only)."""
        info = NPUInfo(core_count=3)  # RK3588 has 3 cores

        if not IS_LINUX:
            # NPU hardware is only available on RK3588 Linux
            info.available = False
            info.driver_version = "N/A (non-Linux platform)"
            return info

        try:
            # Check NPU availability
            npu_paths = [
                "/sys/class/devfreq/fdab0000.npu",
                "/sys/devices/platform/fdab0000.npu",
            ]
            info.available = any(os.path.exists(p) for p in npu_paths)

            # Read per-core usage from debug interface (requires root/sudo)
            debug_load_path = "/sys/kernel/debug/rknpu/load"
            if os.path.exists(debug_load_path):
                try:
                    with open(debug_load_path) as f:
                        content = f.read().strip()
                        # Parse format: "NPU load:  Core0: 21%, Core1:  1%, Core2:  1%,"
                        if "Core0" in content and "Core1" in content and "Core2" in content:
                            core_usages = []
                            for i in range(3):
                                core_label = f"Core{i}:"
                                if core_label in content:
                                    # Extract percentage after "CoreN:"
                                    start = content.index(core_label) + len(core_label)
                                    end = content.index("%", start)
                                    pct_str = content[start:end].strip()
                                    core_usages.append(float(pct_str))

                            if len(core_usages) == 3:
                                info.per_core_usage = core_usages
                                # Average usage across all cores
                                info.usage_percent = round(sum(core_usages) / 3, 1)
                                logger.debug(f"NPU per-core usage: Core0={core_usages[0]}%, Core1={core_usages[1]}%, Core2={core_usages[2]}%")
                            else:
                                logger.warning(f"Failed to parse NPU load from {debug_load_path}: incomplete data")
                        else:
                            logger.warning(f"Failed to parse NPU load from {debug_load_path}: unexpected format")
                except (PermissionError, OSError) as e:
                    logger.warning(
                        f"Cannot read {debug_load_path}: {e}. "
                        f"Run with sudo or grant permissions: sudo chmod +r {debug_load_path}"
                    )
            else:
                logger.warning(f"NPU debug interface not found: {debug_load_path}")

            # Read driver version
            version_paths = [
                "/sys/kernel/debug/rknpu/version",
                "/sys/class/misc/npu/device/driver/module/version",
            ]
            for vp in version_paths:
                if os.path.exists(vp):
                    try:
                        with open(vp) as f:
                            info.driver_version = f.read().strip()
                            break
                    except (PermissionError, OSError):
                        pass

            # If no driver version found, set a default
            if not info.driver_version and info.available:
                info.driver_version = "RK3588"

        except Exception as e:
            logger.debug(f"NPU read error: {e}")

        return info

    def _read_memory(self) -> MemoryInfo:
        """Read memory usage from /proc/meminfo (Linux) or psutil (cross-platform)."""
        info = MemoryInfo()
        try:
            if IS_LINUX:
                self._read_memory_linux(info)
            elif self._psutil:
                vm = self._psutil.virtual_memory()
                info.total_mb = round(vm.total / (1024 ** 2), 1)
                info.available_mb = round(vm.available / (1024 ** 2), 1)
                info.used_mb = round(info.total_mb - info.available_mb, 1)
                info.usage_percent = round(vm.percent, 1)
        except Exception as e:
            logger.debug(f"Memory read error: {e}")
        return info

    def _read_memory_linux(self, info: MemoryInfo) -> None:
        """Read memory via /proc/meminfo (Linux only)."""
        with open("/proc/meminfo") as f:
            meminfo = {}
            for line in f:
                parts = line.split()
                key = parts[0].rstrip(":")
                value_kb = int(parts[1])
                meminfo[key] = value_kb

        info.total_mb = round(meminfo.get("MemTotal", 0) / 1024, 1)
        available_kb = meminfo.get("MemAvailable", meminfo.get("MemFree", 0))
        info.available_mb = round(available_kb / 1024, 1)
        info.used_mb = round(info.total_mb - info.available_mb, 1)
        if info.total_mb > 0:
            info.usage_percent = round(info.used_mb / info.total_mb * 100, 1)

    def _read_temperature(self) -> TemperatureInfo:
        """Read temperature sensors from sysfs (Linux) or psutil (cross-platform)."""
        info = TemperatureInfo()

        if IS_LINUX:
            return self._read_temperature_linux(info)

        # Cross-platform fallback via psutil
        if self._psutil and hasattr(self._psutil, "sensors_temperatures"):
            try:
                temps = self._psutil.sensors_temperatures()
                if temps:
                    for name, entries in temps.items():
                        for entry in entries:
                            label = (entry.label or name).lower()
                            if "cpu" in label or "core" in label:
                                info.cpu_temp = max(info.cpu_temp, round(entry.current, 1))
                            elif "gpu" in label:
                                info.gpu_temp = round(entry.current, 1)
            except Exception as e:
                logger.debug(f"Temperature read (psutil) error: {e}")

        return info

    def _read_temperature_linux(self, info: TemperatureInfo) -> TemperatureInfo:
        """Read temperature via /sys/class/thermal (Linux only)."""
        thermal_base = Path("/sys/class/thermal")
        if not thermal_base.exists():
            return info

        try:
            for zone_dir in sorted(thermal_base.glob("thermal_zone*")):
                type_file = zone_dir / "type"
                temp_file = zone_dir / "temp"
                if not type_file.exists() or not temp_file.exists():
                    continue

                zone_type = type_file.read_text().strip().lower()
                temp_mc = int(temp_file.read_text().strip())
                temp_c = temp_mc / 1000.0

                if "soc" in zone_type or "cpu" in zone_type or "bigcore" in zone_type:
                    info.cpu_temp = max(info.cpu_temp, round(temp_c, 1))
                elif "npu" in zone_type:
                    info.npu_temp = round(temp_c, 1)
                elif "gpu" in zone_type:
                    info.gpu_temp = round(temp_c, 1)

        except Exception as e:
            logger.debug(f"Temperature read error: {e}")

        return info

    def _read_disk(self) -> DiskInfo:
        """Read disk usage (cross-platform via shutil.disk_usage)."""
        info = DiskInfo()
        try:
            # shutil.disk_usage works on all platforms
            disk_path = "/" if IS_LINUX else os.environ.get("SystemDrive", "C:\\")
            usage = shutil.disk_usage(disk_path)
            info.total_gb = round(usage.total / (1024 ** 3), 1)
            info.free_gb = round(usage.free / (1024 ** 3), 1)
            info.used_gb = round(usage.used / (1024 ** 3), 1)
            if info.total_gb > 0:
                info.usage_percent = round(info.used_gb / info.total_gb * 100, 1)
        except Exception as e:
            logger.debug(f"Disk read error: {e}")

        return info

    def _read_network(self) -> list[NetworkInfo]:
        """Read network interface info (cross-platform)."""
        if IS_LINUX:
            return self._read_network_linux()
        return self._read_network_fallback()

    def _read_network_linux(self) -> list[NetworkInfo]:
        """Read network info via /sys/class/net (Linux only)."""
        interfaces = []
        try:
            net_dir = Path("/sys/class/net")
            if not net_dir.exists():
                return interfaces

            for iface_dir in net_dir.iterdir():
                name = iface_dir.name
                if name == "lo":
                    continue

                info = NetworkInfo(interface=name)

                try:
                    import fcntl
                    import struct

                    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
                    info.ip_address = socket.inet_ntoa(
                        fcntl.ioctl(
                            s.fileno(), 0x8915,
                            struct.pack("256s", name.encode("utf-8")[:15]),
                        )[20:24]
                    )
                    s.close()
                except Exception:
                    info.ip_address = ""

                stats_dir = iface_dir / "statistics"
                if stats_dir.exists():
                    try:
                        info.bytes_sent = int((stats_dir / "tx_bytes").read_text().strip())
                        info.bytes_recv = int((stats_dir / "rx_bytes").read_text().strip())
                    except Exception:
                        pass

                interfaces.append(info)

        except Exception as e:
            logger.debug(f"Network read error: {e}")

        return interfaces

    def _read_network_fallback(self) -> list[NetworkInfo]:
        """Read network info using psutil or socket (cross-platform)."""
        interfaces = []
        try:
            if self._psutil:
                addrs = self._psutil.net_if_addrs()
                counters = self._psutil.net_io_counters(pernic=True)
                for name, addr_list in addrs.items():
                    if name == "lo" or name.startswith("Loopback"):
                        continue
                    info = NetworkInfo(interface=name)
                    for addr in addr_list:
                        if addr.family == socket.AF_INET:
                            info.ip_address = addr.address
                            break
                    if name in counters:
                        info.bytes_sent = counters[name].bytes_sent
                        info.bytes_recv = counters[name].bytes_recv
                    interfaces.append(info)
            else:
                # Minimal fallback: hostname IP only
                try:
                    hostname = socket.gethostname()
                    ip = socket.gethostbyname(hostname)
                    interfaces.append(NetworkInfo(interface="default", ip_address=ip))
                except Exception:
                    pass
        except Exception as e:
            logger.debug(f"Network read error (fallback): {e}")

        return interfaces
