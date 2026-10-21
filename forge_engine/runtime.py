from __future__ import annotations
import shutil
import subprocess
from .config import AppConfig

class RuntimeErrorMessage(RuntimeError):
    pass

def docker(args: list[str], capture: bool = False, check: bool = True):
    if not shutil.which("docker"):
        raise RuntimeErrorMessage("Docker CLI not found. Install Docker Engine first.")
    try:
        result = subprocess.run(
            ["docker", *args], text=True, check=False,
            stdout=subprocess.PIPE if capture else None,
            stderr=subprocess.PIPE if capture else None,
        )
    except OSError as e:
        raise RuntimeErrorMessage(f"Cannot execute Docker: {e}") from e
    if check and result.returncode:
        detail = (result.stderr or result.stdout or "").strip() if capture else ""
        raise RuntimeErrorMessage(f"docker {' '.join(args)} failed ({result.returncode})" + (f": {detail}" if detail else ""))
    return result

def exists(kind: str, name: str) -> bool:
    return docker([kind, "inspect", name], capture=True, check=False).returncode == 0

def pull(cfg: AppConfig):
    docker(["pull", cfg.image])

def up(cfg: AppConfig, replace: bool = False):
    if exists("container", cfg.name):
        if not replace:
            docker(["start", cfg.name])
            return
        docker(["rm", "-f", cfg.name])
    if not exists("image", cfg.image):
        pull(cfg)
    for v in cfg.volumes:
        v.host.mkdir(parents=True, exist_ok=True)
    args = ["run", "-d", "--name", cfg.name, "--restart", cfg.restart]
    if cfg.memory:
        args += ["--memory", cfg.memory]
    if cfg.cpus:
        args += ["--cpus", cfg.cpus]
    for p in cfg.ports:
        args += ["-p", f"{cfg.host_ip}:{p.host}:{p.container}/{p.protocol}"]
    for v in cfg.volumes:
        spec = f"type=bind,src={v.host},dst={v.container}"
        if v.readonly:
            spec += ",readonly"
        args += ["--mount", spec]
    args.append(cfg.image)
    docker(args)

def stop(name: str):
    docker(["stop", name])

def restart(name: str):
    docker(["restart", name])

def logs(name: str, follow: bool = False):
    args = ["logs", "--tail", "200"]
    if follow:
        args.append("--follow")
    args.append(name)
    docker(args)

def ps():
    docker(["ps", "-a", "--format", "table {{.Names}}\\t{{.Image}}\\t{{.Status}}\\t{{.Ports}}"])

def remove(name: str):
    # No -v flag: persistent volumes are not removed.
    docker(["rm", "-f", name])

def update(cfg: AppConfig):
    pull(cfg)
    if exists("container", cfg.name):
        docker(["stop", cfg.name], check=False)
        remove(cfg.name)
    up(cfg)
