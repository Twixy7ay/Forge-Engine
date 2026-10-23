from __future__ import annotations
import argparse
import os
import subprocess
import sys
from pathlib import Path
from . import __version__, runtime
from .config import ConfigError, load_config
from .runtime import RuntimeErrorMessage


def config_dir() -> Path:
    return Path(os.environ.get("FORGE_CONFIG_DIR", Path.home() / ".config" / "forge")).expanduser()

def apps_dir() -> Path: return config_dir() / "apps"
def repos_dir() -> Path: return config_dir() / "repositories"
def repo_file() -> Path: return config_dir() / "repositories.txt"

def app_config(app: str) -> Path:
    if not app or app in {".", ".."} or "/" in app or "\\" in app:
        raise ConfigError("App name must not be a path")
    path = apps_dir() / f"{app}.conf"
    if not path.is_file(): raise ConfigError(f"Configuration not found: {path}")
    return path

def load_app(app: str): return load_config(app_config(app))

def confirm(message: str, yes: bool = False) -> bool:
    if yes: return True
    try: return input(f"{message} [y/N] ").strip().lower() in {"y", "yes"}
    except (EOFError, KeyboardInterrupt):
        print("\nCancelled."); return False

def repository_urls() -> list[str]:
    if not repo_file().exists(): return []
    return [x.strip() for x in repo_file().read_text(encoding="utf-8").splitlines() if x.strip() and not x.strip().startswith("#")]

def save_repositories(urls: list[str]):
    config_dir().mkdir(parents=True, exist_ok=True)
    repo_file().write_text("\n".join(urls) + ("\n" if urls else ""), encoding="utf-8")

def sync_repositories():
    repos_dir().mkdir(parents=True, exist_ok=True)
    urls = repository_urls()
    for i, url in enumerate(urls, 1):
        name = repo_name(url); target = repos_dir() / name
        if target.exists():
            print(f"Updating {name}...")
            subprocess.run(["git", "-C", str(target), "pull", "--ff-only"], check=True)
        else:
            print(f"Cloning {name}...")
            subprocess.run(["git", "clone", "--depth", "1", url, str(target)], check=True)
        print(f"[{i}/{len(urls)}] {name}: ready")
    import_apps()

def repo_name(url: str) -> str:
    name = url.rstrip("/").split("/")[-1]
    if name.endswith(".git"): name = name[:-4]
    if not name or name in {".", ".."} or any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_.-" for c in name):
        raise ConfigError(f"Invalid repository URL/name: {url}")
    return name

def import_apps():
    apps_dir().mkdir(parents=True, exist_ok=True)
    for repo in repos_dir().iterdir() if repos_dir().exists() else []:
        if not repo.is_dir(): continue
        for path in repo.rglob("*.conf"):
            # App names are filenames; avoid collisions and never overwrite local configs.
            target = apps_dir() / path.name
            if not target.exists(): target.write_bytes(path.read_bytes())

def list_apps():
    files = sorted(apps_dir().glob("*.conf")) if apps_dir().exists() else []
    if not files: print(f"No apps found in {apps_dir()}"); return
    for path in files:
        try:
            cfg = load_config(path); print(f"{path.stem:24} {cfg.image}")
        except ConfigError as e: print(f"{path.stem:24} INVALID: {e}")

def menu():
    while True:
        print("\n╔══════════════════════════════════╗\n║          FORGE ENGINE           ║\n╠══════════════════════════════════╣\n║  1. Anwendungen installieren      ║\n║  2. Installierte Apps verwalten  ║\n║  3. Container anzeigen           ║\n║  4. Logs anzeigen                ║\n║  5. Konfiguration prüfen         ║\n║  6. App-Repositories verwalten   ║\n║  7. Docker-Images verwalten      ║\n║  8. Systeminformationen           ║\n║  0. Beenden                      ║\n╚══════════════════════════════════╝")
        try: choice = input("Auswahl: ").strip()
        except (EOFError, KeyboardInterrupt): print(); return
        try:
            if choice == "0": return
            elif choice == "1":
                list_apps(); app = input("App installieren (Name, leer zurück): ").strip()
                if app: runtime.up(load_app(app))
            elif choice == "2":
                runtime.ps(); app = input("App verwalten (Name, leer zurück): ").strip()
                if app:
                    print("1 Start  2 Stop  3 Neustart  4 Logs  5 Entfernen")
                    action = input("Aktion: ").strip(); cfg = load_app(app)
                    if action == "1": runtime.up(cfg)
                    elif action == "2": runtime.stop(cfg.name)
                    elif action == "3": runtime.restart(cfg.name)
                    elif action == "4": runtime.logs(cfg.name, True)
                    elif action == "5" and confirm(f"Container {cfg.name} entfernen? Daten bleiben erhalten."): runtime.remove(cfg.name)
            elif choice == "3": runtime.ps()
            elif choice == "4":
                app = input("Containername: ").strip()
                if app: runtime.logs(app, True)
            elif choice == "5": validate_configs()
            elif choice == "6": repository_menu()
            elif choice == "7": image_menu()
            elif choice == "8": system_info()
            else: print("Ungültige Auswahl.")
        except (ConfigError, RuntimeErrorMessage, subprocess.CalledProcessError) as e: print(f"forge: {e}", file=sys.stderr)

def validate_configs():
    paths = sorted(apps_dir().glob("*.conf")) if apps_dir().exists() else []
    if not paths: print(f"No .conf files found in {apps_dir()}"); return
    failed = False
    for path in paths:
        try: cfg = load_config(path); print(f"OK   {path.name}: {cfg.name} -> {cfg.image}")
        except ConfigError as e: failed = True; print(f"FAIL {path.name}: {e}", file=sys.stderr)
    if failed: raise ConfigError("One or more app configs are invalid")

def repository_menu():
    while True:
        print("\nRepositories:")
        for i, url in enumerate(repository_urls(), 1): print(f" {i}. {url}")
        print(" a) hinzufügen  u) aktualisieren/importieren  r) entfernen  0) zurück")
        action = input("Auswahl: ").strip().lower()
        urls = repository_urls()
        if action == "0": return
        if action == "a":
            url = input("Git-Repository-URL: ").strip()
            if url and url not in urls: urls.append(url); save_repositories(urls)
        elif action == "u": sync_repositories()
        elif action == "r":
            raw = input("Nummer: ").strip()
            if raw.isdigit() and 1 <= int(raw) <= len(urls):
                if confirm(f"Repository {urls[int(raw)-1]} aus Liste entfernen? (lokale Dateien bleiben)"):
                    urls.pop(int(raw)-1); save_repositories(urls)
        else: print("Ungültige Auswahl.")

def image_menu():
    print("Docker images:")
    runtime.docker(["images", "--format", "table {{.Repository}}:{{.Tag}}\t{{.Size}}"])
    print("\n1. Image herunterladen  2. Image löschen  0. zurück")
    action = input("Auswahl: ").strip()
    if action == "1":
        image = input("Image (name:tag): ").strip()
        if image: runtime.docker(["pull", image])
    elif action == "2":
        image = input("Image (name:tag): ").strip()
        if image and confirm(f"Image {image} entfernen?"): runtime.docker(["image", "rm", image])

def system_info():
    print(f"Forge Engine {__version__}\nPython: {sys.version.split()[0]}\nConfig: {config_dir()}\nApps: {apps_dir()}\nDocker:")
    runtime.docker(["version", "--format", "{{.Client.Version}} (client) / {{.Server.Version}} (server)"])

def parser():
    p = argparse.ArgumentParser(prog="forge", description="Forge Engine: .conf-driven container CLI")
    p.add_argument("--version", action="version", version=f"Forge Engine {__version__}")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("init"); sub.add_parser("menu"); sub.add_parser("apps")
    cfg = sub.add_parser("config"); cfgsub = cfg.add_subparsers(dest="config_command", required=True); cfgsub.add_parser("validate")
    repo = sub.add_parser("repo"); reposub = repo.add_subparsers(dest="repo_command", required=True)
    reposub.add_parser("list"); reposub.add_parser("sync")
    add = reposub.add_parser("add"); add.add_argument("url")
    rem = reposub.add_parser("remove"); rem.add_argument("index", type=int)
    sub.add_parser("ps")
    for command in ("pull", "up", "stop", "restart", "logs", "down", "update"):
        c = sub.add_parser(command); c.add_argument("app")
        if command == "logs": c.add_argument("-f", "--follow", action="store_true")
        if command in ("down", "update"): c.add_argument("-y", "--yes", action="store_true")
    return p

def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "init":
            apps_dir().mkdir(parents=True, exist_ok=True); config_dir().mkdir(parents=True, exist_ok=True)
            example = apps_dir() / "example.conf"
            if not example.exists(): example.write_text("[container]\nname = example\nimage = traefik/whoami:v1.11\nrestart = unless-stopped\n\n[network]\nhost_ip = 127.0.0.1\nports = 8080:80\n\n[storage]\nvolumes =\n\n[resources]\nmemory = 256m\ncpus = 0.5\n", encoding="utf-8")
            print(f"Forge initialized at {config_dir()}\nExample: {example}"); return 0
        if args.command == "menu": menu(); return 0
        if args.command == "apps": list_apps(); return 0
        if args.command == "config": validate_configs(); return 0
        if args.command == "repo":
            urls = repository_urls()
            if args.repo_command == "list":
                for i, url in enumerate(urls, 1): print(f"{i}. {url}")
            elif args.repo_command == "sync": sync_repositories()
            elif args.repo_command == "add":
                if args.url not in urls: urls.append(args.url); save_repositories(urls)
                sync_repositories()
            elif args.repo_command == "remove":
                if not 1 <= args.index <= len(urls): raise ConfigError("Repository index out of range")
                urls.pop(args.index-1); save_repositories(urls)
            return 0
        if args.command == "ps": runtime.ps(); return 0
        cfg = load_app(args.app)
        if args.command == "pull": runtime.pull(cfg)
        elif args.command == "up": runtime.up(cfg)
        elif args.command == "stop": runtime.stop(cfg.name)
        elif args.command == "restart": runtime.restart(cfg.name)
        elif args.command == "logs": runtime.logs(cfg.name, args.follow)
        elif args.command == "down":
            if not confirm(f"Remove container {cfg.name}? Persistent data will be kept.", args.yes): return 1
            runtime.remove(cfg.name)
        elif args.command == "update":
            if not confirm(f"Pull and recreate {cfg.name} using {cfg.image}?", args.yes): return 1
            runtime.update(cfg)
        return 0
    except (ConfigError, RuntimeErrorMessage, subprocess.CalledProcessError) as e:
        print(f"forge: error: {e}", file=sys.stderr); return 1
    except KeyboardInterrupt: print("\nCancelled.", file=sys.stderr); return 130

if __name__ == "__main__": raise SystemExit(main())
