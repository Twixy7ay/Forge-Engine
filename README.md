# Forge Engine

Forge Engine is an experimental `.conf`-driven container CLI using Docker as its initial runtime. It is a management layer, not an independent container runtime.

## Requirements
- Linux (Ubuntu Server recommended), Python 3.10+
- Docker Engine and Docker CLI
- Docker daemon access (equivalent to host-level administrative access)

## Install
```bash
git clone https://github.com/YOUR-USERNAME/forge-engine.git
cd forge-engine
python3 -m venv .venv
. .venv/bin/activate
pip install -e .
forge init
```

To use `/etc/forge`, create it and grant your account access, then set `FORGE_CONFIG_DIR=/etc/forge`. By default Forge uses `~/.config/forge`.

## Quick start
```bash
forge init
# Edit ~/.config/forge/apps/example.conf
forge config validate
forge pull example
forge up example
forge ps
forge logs example
```

Example `.conf`:
```ini
[container]
name = whoami
image = traefik/whoami:v1.11
restart = unless-stopped

[network]
host_ip = 127.0.0.1
ports = 8080:80

[storage]
volumes =

[resources]
memory = 256m
cpus = 0.5
```

Published ports bind to `127.0.0.1` by default. Setting `host_ip = 0.0.0.0` exposes the port on all host interfaces; only do this intentionally and configure your firewall. Forge does not create router port forwards.

## Commands
- `forge init`
- `forge config validate`
- `forge pull APP`
- `forge up APP`
- `forge stop APP`
- `forge restart APP`
- `forge logs APP [--follow]`
- `forge ps`
- `forge down APP [--yes]`
- `forge update APP [--yes]`

`down` removes the container but does not delete bind-mounted data or named volumes. `update` recreates the container and asks for confirmation by default.

## Safety / limitations
- This is an MVP, not security-audited.
- Docker daemon access is highly privileged.
- Review `.conf` files before applying them.
- Do not store secrets in `.conf` files.
- The MVP does not yet have a background controller, automatic config watching, a registry service, image-signature verification, or its own runtime.
- Test on a non-critical machine first.

## Tests
```bash
python -m unittest discover -s tests -v
```

## Publish to GitHub
Create an empty repository on GitHub, then run:
```bash
git init
git add .
git commit -m "Initial Forge Engine MVP"
git branch -M main
git remote add origin https://github.com/YOUR-USERNAME/forge-engine.git
git push -u origin main
```
Replace `YOUR-USERNAME`. This archive does not create or push a repository to your account automatically.
