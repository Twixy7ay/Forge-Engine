from __future__ import annotations
import configparser
import ipaddress
import re
from dataclasses import dataclass
from pathlib import Path

class ConfigError(ValueError):
    pass

@dataclass(frozen=True)
class Port:
    host: int
    container: int
    protocol: str

@dataclass(frozen=True)
class Volume:
    host: Path
    container: str
    readonly: bool

@dataclass(frozen=True)
class AppConfig:
    name: str
    image: str
    restart: str
    host_ip: str
    ports: tuple[Port, ...]
    volumes: tuple[Volume, ...]
    memory: str | None
    cpus: str | None

def _csv(value: str) -> list[str]:
    return [x.strip() for x in value.split(",") if x.strip()]

def load_config(path: Path) -> AppConfig:
    p = configparser.ConfigParser(interpolation=None)
    try:
        with path.open(encoding="utf-8") as f:
            p.read_file(f)
    except (OSError, configparser.Error) as e:
        raise ConfigError(f"Cannot read/parse {path}: {e}") from e

    allowed = {"container", "network", "storage", "resources"}
    unknown = set(p.sections()) - allowed
    if unknown:
        raise ConfigError(f"Unknown sections: {', '.join(sorted(unknown))}")
    if not p.has_section("container"):
        raise ConfigError("Missing [container] section")

    name = p.get("container", "name", fallback=path.stem).strip()
    image = p.get("container", "image", fallback="").strip()
    restart = p.get("container", "restart", fallback="unless-stopped").strip()
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,62}", name):
        raise ConfigError("Invalid container name")
    if not image or any(c.isspace() for c in image) or image.startswith("-"):
        raise ConfigError("A valid image name is required")
    if restart not in {"no", "always", "unless-stopped", "on-failure"}:
        raise ConfigError("Invalid restart policy")

    host_ip = p.get("network", "host_ip", fallback="127.0.0.1").strip()
    try:
        ipaddress.ip_address(host_ip)
    except ValueError as e:
        raise ConfigError(f"Invalid host_ip: {host_ip}") from e

    ports = []
    for item in _csv(p.get("network", "ports", fallback="")):
        m = re.fullmatch(r"(\d{1,5}):(\d{1,5})(?:/(tcp|udp))?", item)
        if not m:
            raise ConfigError(f"Invalid port mapping {item!r}; use HOST:CONTAINER[/tcp|udp]")
        h, c = int(m.group(1)), int(m.group(2))
        if not 1 <= h <= 65535 or not 1 <= c <= 65535:
            raise ConfigError(f"Port out of range: {item}")
        ports.append(Port(h, c, m.group(3) or "tcp"))

    volumes = []
    for item in _csv(p.get("storage", "volumes", fallback="")):
        bits = item.split(":")
        if len(bits) not in (2, 3) or (len(bits) == 3 and bits[2] != "ro"):
            raise ConfigError(f"Invalid volume {item!r}; use /host:/container[:ro]")
        host, container = Path(bits[0]).expanduser(), bits[1]
        if not host.is_absolute():
            raise ConfigError(f"Host volume path must be absolute: {host}")
        if not container.startswith("/") or ".." in Path(container).parts:
            raise ConfigError(f"Invalid container path: {container}")
        volumes.append(Volume(host, container, len(bits) == 3))

    memory = p.get("resources", "memory", fallback="").strip() or None
    cpus = p.get("resources", "cpus", fallback="").strip() or None
    if memory and not re.fullmatch(r"\d+[kKmMgG]?", memory):
        raise ConfigError("Invalid memory limit, example: 256m")
    if cpus:
        try:
            n = float(cpus)
        except ValueError as e:
            raise ConfigError("Invalid CPU limit") from e
        if not 0 < n <= 1024:
            raise ConfigError("CPU limit must be > 0 and <= 1024")

    return AppConfig(name, image, restart, host_ip, tuple(ports), tuple(volumes), memory, cpus)
