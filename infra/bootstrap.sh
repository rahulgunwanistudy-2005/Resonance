#!/usr/bin/env bash
set -euo pipefail
cd /opt/resonance
python3.12 -m venv --system-site-packages .venv
# Never install the 'local' extra on COOL: it would shadow /opt/cool OpenCV.
if ! command -v uv >/dev/null; then
  .venv/bin/python -m pip install 'uv==0.8.22'
fi
UV_PROJECT_ENVIRONMENT=../.venv uv sync --project engine --extra service --extra report --no-dev --frozen --inexact
.venv/bin/python scripts/verify_cool.py --output outputs/cool-runtime.json
.venv/bin/python -c "import shutil; assert shutil.which('ffprobe'), 'Install FFmpeg for this AMI before continuing'"
install -d -m 700 outputs
if [ ! -f outputs/local-admin-token ]; then
  .venv/bin/python -c "import secrets,pathlib; p=pathlib.Path('outputs/local-admin-token');p.write_text(secrets.token_urlsafe(32));p.chmod(0o600)"
fi
cat >/etc/systemd/system/resonance.service <<'SERVICE'
[Unit]
Description=Resonance local service on COOL
After=network-online.target
[Service]
WorkingDirectory=/opt/resonance
ExecStart=/opt/resonance/.venv/bin/python -m scripts.run_local
Restart=on-failure
Environment=RESONANCE_HOST=0.0.0.0
Environment=MPLCONFIGDIR=/opt/resonance/outputs/matplotlib
NoNewPrivileges=true
PrivateTmp=true
UMask=0077
[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable --now resonance
