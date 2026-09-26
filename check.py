#!/usr/bin/env python3

import argparse
import json
import os
import subprocess
import sys

VERSION = "1.0.0"

RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
RESET = "\033[0m"

SKIP_FSTYPES = {"tmpfs", "devtmpfs"}


def ports_list(str) -> list[int]:
    ports = []
    for item in str.split(","):
        ports.append(int(item))
    return ports


def units_list(str) -> list[str]:
    units = str.split(",")
    return units


def check_port(ports: list[int]) -> list[dict]:
    status = []
    ipv4_ports = get_ipv4()
    ipv6_ports = get_ipv6()
    for port in ports:
        on_v4 = port in ipv4_ports
        on_v6 = port in ipv6_ports
        if on_v4:
            print(f"{BLUE}[IPv4]{RESET} Listening {port}")
        if on_v6:
            print(f"{BLUE}[IPv6]{RESET} Listening {port}")
        if port not in ipv4_ports and port not in ipv6_ports:
            print(f"{YELLOW}[Port] {port} is not listening{RESET}")
        status.append({"port": port, "ipv4": on_v4, "ipv6": on_v6})
    return status


def check_unit(units: list[str]) -> list[dict]:
    status = []
    for unit in units:
        try:
            result = subprocess.run(
                ["systemctl", "is-active", unit],
                capture_output=True,
                text=True,
                check=False,
            )
        except FileNotFoundError:
            print(f"{RED}[ERROR] systemctl not found{RESET}")
            status.append({"unit": unit, "status": ""})
            continue

        active = result.stdout.strip() == "active"
        if active:
            print(f"{BLUE}[Unit]{RESET} Active: {unit}")
        else:
            print(f"{YELLOW}[Unit] inactive: {unit}{RESET}")
        status.append({"unit": unit, "status": "active" if active else "inactive"})
    return status


def check_partition(threshold: float) -> list[dict]:
    status = []
    for mount in get_mounts():
        state = os.statvfs(mount)
        if state.f_blocks == 0:
            continue
        used = (state.f_blocks - state.f_bfree) * state.f_frsize
        avaliable = state.f_bavail * state.f_frsize
        percent = used * 100 / (used + avaliable)
        over = percent >= threshold
        if over:
            print(f"{RED}[Partition] {mount}: {percent:.1f}%{RESET}")
        else:
            print(f"{BLUE}[Partition] {mount}: {percent:.1f}%{RESET}")
        status.append({"partition": mount, "percent": round(percent, 1), "over": over})
    return status


def get_mounts() -> list[str]:
    mounts = []
    with open("/proc/mounts") as file:
        for line in file:
            line = line.split()
            if line[2] in SKIP_FSTYPES:
                continue
            mounts.append(line[1])
    return mounts


def get_active_units() -> list[str]:
    """
    Return the list of active systemd services.
    """
    units = []
    output = subprocess.run(
        [
            "systemctl",
            "list-units",
            "--type",
            "service",
            "--state",
            "active",
            "--no-legend",
            "--no-pager",
            "--plain",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    for service in output.stdout.splitlines():
        units.append(service.split()[0])
    return units


def get_ipv4() -> list[int]:
    """
    Return the list of listening IPv4 TCP ports.
    """
    ports = []
    lines = ""
    with open("/proc/net/tcp") as tcp:
        lines = tcp.readlines()
    for line in lines:
        line = line.split()
        if line[3] == "0A":
            ports.append(int(line[1].split(":")[1], 16))
    return ports


def get_ipv6() -> list[int]:
    """
    Return the list of listening IPv6 TCP ports.
    """
    ports = []
    lines = ""
    with open("/proc/net/tcp6") as tcp6:
        lines = tcp6.readlines()
    for line in lines:
        line = line.split()
        if line[3] == "0A":
            ports.append(int(line[1].split(":")[1], 16))
    return ports


def parse_args():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "-v", "-V", "--version", action="version", version=f"%(prog)s {VERSION}"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="output.json",
        help="which file to output (default output.json)",
    )
    parser.add_argument(
        "-u",
        "--unit",
        type=units_list,
        default=[],
        help="systemd services to check, comma-seperated",
    )
    parser.add_argument(
        "-p",
        "--port",
        type=ports_list,
        default=[],
        help="ports to check, comma-seperated",
    )
    parser.add_argument(
        "-t", "--threshold", type=float, default=85, help="threshold for disk warning"
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    args = parse_args()
    results = {
        "units": check_unit(args.unit),
        "ports": check_port(args.port),
        "partitions": check_partition(args.threshold),
    }
    text = json.dumps(results, indent=2)
    with open(args.output, "w") as file:
        file.write(text + "\n")

    failed = (
        any(unit["status"] != "active" for unit in results["units"])
        or any(not port["ipv4"] and not port["ipv6"] for port in results["ports"])
        or any(partition["over"] for partition in results["partitions"])
    )
    sys.exit(1 if failed else 0)
