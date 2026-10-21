from __future__ import annotations
import argparse
import os
import sys
from pathlib import Path
from . import __version__
from .config import ConfigError, load_config
from . import runtime
from .runtime import RuntimeErrorMessage

def config_dir() -> Path:
    return Path(os.environ.get("FORGE_CONFIG_DIR", Path.home() / ".config" / "forge")).expanduser()

def apps_dir() -> Path:
    return config_dir() / "apps"

def app_config(app: str) -> Path:
    if not app or app in {".", ".."} or "/" in app or "\\" in app:
        raise ConfigError("App name must not be a path")
    path = apps_dir() / f"{app}.conf"
    if not path.is_file():
        raise ConfigError(f"Configuration not found: {path}")
    return path

def load_app(app: str):
    return load_config(app_config(app))

def confirm(message: str, yes: bool) -> bool:
    if yes:
        return True
    try:
        return input(f"{message} [y/N] ").strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled.")
        return False

def parser():
    p = argparse.ArgumentParser(prog="forge", description="Forge Engine: .conf-driven container CLI")
    p.add_argument("--version", action="version", version=f"Forge Engine {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init")
    cfg = sub.add_parser("config")
    cfgsub = cfg.add_subparsers(dest="config_command", required=True)
    cfgsub.add_parser("validate")
    sub.add_parser("ps")
    for command in ("pull", "up", "stop", "restart", "logs", "down", "update"):
        c = sub.add_parser(command)
        c.add_argument("app")
        if command == "logs":
            c.add_argument("-f", "--follow", action="store_true")
        if command in ("down", "update"):
            c.add_argument("-y", "--yes", action="store_true")
    return p

def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            apps_dir().mkdir(parents=True, exist_ok=True)
            (config_dir() / "logs").mkdir(parents=True, exist_ok=True)
            example = apps_dir() / "example.conf"
            if not example.exists():
                example.write_text(
                    "[container]\\nname = example\\nimage = traefik/whoami:v1.11\\nrestart = unless-stopped\\n\\n"
                    "[network]\\nhost_ip = 127.0.0.1\\nports = 8080:80\\n\\n"
                    "[storage]\\nvolumes =\\n\\n[resources]\\nmemory = 256m\\ncpus = 0.5\\n",
                    encoding="utf-8")
            print(f"Forge initialized at {config_dir()}")
            print(f"Example: {example}")
            return 0
        if args.command == "config":
            paths = sorted(apps_dir().glob("*.conf"))
            if not paths:
                print(f"No .conf files found in {apps_dir()}")
                return 1
            failed = False
            for path in paths:
                try:
                    cfg = load_config(path)
                    print(f"OK   {path.name}: {cfg.name} -> {cfg.image}")
                except ConfigError as e:
                    failed = True
                    print(f"FAIL {path.name}: {e}", file=sys.stderr)
            return int(failed)
        if args.command == "ps":
            runtime.ps()
            return 0

        cfg = load_app(args.app)
        if args.command == "pull":
            runtime.pull(cfg)
        elif args.command == "up":
            runtime.up(cfg)
        elif args.command == "stop":
            runtime.stop(cfg.name)
        elif args.command == "restart":
            runtime.restart(cfg.name)
        elif args.command == "logs":
            runtime.logs(cfg.name, args.follow)
        elif args.command == "down":
            if not confirm(f"Remove container {cfg.name}? Persistent data will be kept.", args.yes):
                return 1
            runtime.remove(cfg.name)
        elif args.command == "update":
            if not confirm(f"Pull and recreate {cfg.name} using {cfg.image}?", args.yes):
                return 1
            runtime.update(cfg)
        return 0
    except (ConfigError, RuntimeErrorMessage) as e:
        print(f"forge: error: {e}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nCancelled.", file=sys.stderr)
        return 130

if __name__ == "__main__":
    raise SystemExit(main())
