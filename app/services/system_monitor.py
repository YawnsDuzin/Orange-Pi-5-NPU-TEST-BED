"""
System Monitor Module

Monitors hardware resources: CPU, NPU, memory, temperature, and disk.
Optimized for Orange Pi 5 Plus (RK3588) with sysfs-based readings.
"""

import asyncio
import logging
import os
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


class SystemMonitor:
    """
    System Monitor - periodic hardware status polling.

    Reads hardware metrics from /proc and /sys on Linux.
    Designed for Orange Pi 5 Plus (RK3588) but degrades gracefully
    on other platforms.
    """

    def __init__(self, poll_interval: float = 2.0):
        self._poll_interval = poll_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None
        self._status = SystemStatus()
        self._start_time = time.monotonic()

        # For CPU usage delta calculation
        self._prev_cpu_times: Optional[list[int]] = None

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
        loop = asyncio.get_event_loop()
        status = await loop.run_in_executor(None, self._read_all_metrics)
        self._status = status
        return status

    async def _monitor_loop(self) -> None:
        """Periodic monitoring loop."""
        loop = asyncio.get_event_loop()
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
        """Read CPU usage from /proc/stat."""
        info = CPUInfo()
        try:
            with open("/proc/stat") as f:
                lines = f.readlines()

            # Parse total CPU line
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

            # Core count
            info.core_count = sum(1 for l in lines if l.startswith("cpu") and l[3:4].isdigit())

            # Frequency
            freq_path = "/sys/devices/system/cpu/cpu0/cpufreq/scaling_cur_freq"
            if os.path.exists(freq_path):
                with open(freq_path) as f:
                    info.frequency_mhz = round(int(f.read().strip()) / 1000, 0)

            # Per-core usage (simplified)
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

        except Exception as e:
            logger.debug(f"CPU read error: {e}")

        return info

    def _read_npu(self) -> NPUInfo:
        """Read NPU status from sysfs."""
        info = NPUInfo(core_count=3)  # RK3588 has 3 cores

        try:
            # Check NPU availability
            npu_paths = ["/dev/rknpu", "/sys/class/misc/npu"]
            info.available = any(os.path.exists(p) for p in npu_paths)

            # Read NPU load (RK3588 specific)
            load_path = "/sys/kernel/debug/rknpu/load"
            if os.path.exists(load_path):
                try:
                    with open(load_path) as f:
                        content = f.read().strip()
                        # Parse NPU load percentage
                        for line in content.split("\n"):
                            if "%" in line:
                                pct = line.split("%")[0].strip().split()[-1]
                                info.usage_percent = float(pct)
                                break
                except (PermissionError, OSError):
                    pass

            # Driver version
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

        except Exception as e:
            logger.debug(f"NPU read error: {e}")

        return info

    def _read_memory(self) -> MemoryInfo:
        """Read memory usage from /proc/meminfo."""
        info = MemoryInfo()
        try:
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

        except Exception as e:
            logger.debug(f"Memory read error: {e}")

        return info

    def _read_temperature(self) -> TemperatureInfo:
        """Read temperature sensors from sysfs."""
        info = TemperatureInfo()

        # RK3588 thermal zones (may vary by board)
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
        """Read disk usage for root filesystem."""
        info = DiskInfo()
        try:
            stat = os.statvfs("/")
            info.total_gb = round(stat.f_frsize * stat.f_blocks / (1024 ** 3), 1)
            info.free_gb = round(stat.f_frsize * stat.f_bavail / (1024 ** 3), 1)
            info.used_gb = round(info.total_gb - info.free_gb, 1)
            if info.total_gb > 0:
                info.usage_percent = round(info.used_gb / info.total_gb * 100, 1)
        except Exception as e:
            logger.debug(f"Disk read error: {e}")

        return info

    def _read_network(self) -> list[NetworkInfo]:
        """Read network interface info."""
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

                # Read IP (from /proc/net/fib_trie or socket)
                try:
                    import socket
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

                # Read bytes
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
