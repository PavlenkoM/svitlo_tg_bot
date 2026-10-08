#!/usr/bin/env bash
# Install / update svitlo_tg_bot on Raspberry Pi (Debian / Raspberry Pi OS) and run it with pm2.
# Safe to run again: existing venv, config and pm2 process are reused.
#
#   ./install.sh                  # install or update, process name 'svitlo-bot'
#   APP_NAME=my-bot ./install.sh  # custom pm2 process name for a new install

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_NAME="${APP_NAME:-svitlo-bot}"
VENV_DIR="$APP_DIR/venv"
VENV_PY="$VENV_DIR/bin/python"
CONFIG_FILE="$APP_DIR/config/config.yaml"
MAIN_FILE="$APP_DIR/main.py"

GREEN='\033[92m'; YELLOW='\033[93m'; RED='\033[91m'; BLUE='\033[94m'; RESET='\033[0m'
step()  { echo -e "\n${BLUE}==> $*${RESET}"; }
ok()    { echo -e "${GREEN}✅ $*${RESET}"; }
warn()  { echo -e "${YELLOW}⚠️  $*${RESET}"; }
fail()  { echo -e "${RED}❌ $*${RESET}"; exit 1; }

# Single-quoted YAML string: ' is escaped as ''
yamlQuote() { local q="'"; printf "'%s'" "${1//$q/$q$q}"; }

if [[ $EUID -eq 0 ]]; then
    fail "Run as a regular user (not root). The script uses sudo when needed."
fi

# ---------------------------------------------------------------------------
step "System packages"

missingPackages=()
for package in git python3 python3-venv python3-pip; do
    dpkg -s "$package" &>/dev/null || missingPackages+=("$package")
done

if (( ${#missingPackages[@]} )); then
    echo "Installing: ${missingPackages[*]}"
    sudo apt-get update
    sudo apt-get install -y "${missingPackages[@]}"
fi
ok "Python: $(python3 --version)"

# ---------------------------------------------------------------------------
step "pm2"

if ! command -v pm2 &>/dev/null; then
    if ! command -v npm &>/dev/null; then
        echo "Installing Node.js and npm"
        sudo apt-get update
        sudo apt-get install -y nodejs npm
    fi
    echo "Installing pm2"
    sudo npm install -g pm2
fi
ok "pm2 $(pm2 --version)"

# ---------------------------------------------------------------------------
step "Python virtual environment"

if [[ ! -x "$VENV_PY" ]]; then
    python3 -m venv "$VENV_DIR"
    ok "Created $VENV_DIR"
fi
"$VENV_PY" -m pip install --quiet --upgrade pip
"$VENV_PY" -m pip install --quiet -r "$APP_DIR/requirements.txt"
ok "Dependencies installed"

# ---------------------------------------------------------------------------
step "Configuration"

discoverLoggers() {
    # Prints "ip serial" for every Solarman logger that answers the broadcast
    "$VENV_PY" - <<'EOF'
import socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
sock.settimeout(3)
sock.sendto(b'WIFIKIT-214028-READ', ('255.255.255.255', 48899))
try:
    while True:
        data, _ = sock.recvfrom(1024)
        parts = data.decode(errors='replace').split(',')
        if len(parts) >= 3:
            print(parts[0], parts[2])
except socket.timeout:
    pass
EOF
}

if [[ -f "$CONFIG_FILE" ]]; then
    ok "Using existing $CONFIG_FILE"
else
    echo "config/config.yaml not found. Let's create it."

    read -rp "Telegram bot token (from @BotFather): " tgToken
    [[ -n "$tgToken" ]] || fail "Telegram token is required"

    echo "How to detect electricity:"
    echo "  1) deye-local - read grid voltage from Deye inverter WiFi logger"
    echo "  2) ping       - ping a device powered only from the city grid"
    read -rp "Choose [1]: " methodChoice

    if [[ "${methodChoice:-1}" == "2" ]]; then
        read -rp "IP address to ping: " pingIp
        [[ -n "$pingIp" ]] || fail "IP address is required"

        cat > "$CONFIG_FILE" <<EOF
telegram-token: $(yamlQuote "$tgToken")
check-method: 'ping'
ip-address: $(yamlQuote "$pingIp")
EOF
    else
        echo "Searching for inverter loggers in the local network..."
        loggers="$(discoverLoggers 2>/dev/null || true)"
        loggerIp=""; loggerSerial=""

        if [[ -n "$loggers" ]]; then
            echo "Found:"
            echo "$loggers" | sed 's/^/  /'
            read -r loggerIp loggerSerial <<< "$(echo "$loggers" | head -n 1)"
        else
            warn "No loggers answered. Enter the values manually (serial is on the logger sticker)."
        fi

        read -rp "Logger IP [${loggerIp}]: " inputIp
        read -rp "Logger serial number [${loggerSerial}]: " inputSerial
        loggerIp="${inputIp:-$loggerIp}"
        loggerSerial="${inputSerial:-$loggerSerial}"

        [[ -n "$loggerIp" ]] || fail "Logger IP is required"
        [[ "$loggerSerial" =~ ^[0-9]+$ ]] || fail "Logger serial must be a number"

        cat > "$CONFIG_FILE" <<EOF
telegram-token: $(yamlQuote "$tgToken")
check-method: 'deye-local'
deye-local:
  logger-ip: $(yamlQuote "$loggerIp")
  logger-serial: $loggerSerial
EOF
    fi

    chmod 600 "$CONFIG_FILE"
    ok "Created $CONFIG_FILE (all options: config/example_config.yaml)"
fi

# ---------------------------------------------------------------------------
if grep -qE "^check-method:\s*'?deye-local" "$CONFIG_FILE"; then
    step "Checking inverter connection"
    if (cd "$APP_DIR" && "$VENV_PY" deyeProbe.py); then
        ok "Inverter responded"
    else
        warn "Could not read the inverter. Check logger-ip / logger-serial in $CONFIG_FILE"
        warn "The bot will still start and keep the state UNKNOWN until the inverter responds."
    fi
fi

# ---------------------------------------------------------------------------
step "Starting with pm2"

# Reuse a pm2 process that already runs this main.py, whatever its name
existingName="$(pm2 jlist 2>/dev/null | "$VENV_PY" -c '
import json, sys
try:
    processes = json.load(sys.stdin)
except ValueError:
    processes = []
for process in processes:
    if process.get("pm2_env", {}).get("pm_exec_path") == sys.argv[1]:
        print(process["name"])
        break
' "$MAIN_FILE")"

if [[ -n "$existingName" ]]; then
    APP_NAME="$existingName"
    echo "Re-creating existing pm2 process '$APP_NAME' to use the venv interpreter"
    pm2 delete "$APP_NAME" >/dev/null
fi

pm2 start "$MAIN_FILE" \
    --name "$APP_NAME" \
    --cwd "$APP_DIR" \
    --interpreter "$VENV_PY" \
    --interpreter-args="-u"
pm2 save
ok "Bot is running as '$APP_NAME'"

# ---------------------------------------------------------------------------
step "Autostart after reboot"

if systemctl list-unit-files "pm2-$USER.service" &>/dev/null \
    && systemctl is-enabled "pm2-$USER.service" &>/dev/null; then
    ok "Already enabled"
else
    sudo env PATH="$PATH:$(dirname "$(command -v node)")" \
        "$(command -v pm2)" startup systemd -u "$USER" --hp "$HOME"
    pm2 save
    ok "Enabled"
fi

echo
ok "Done!"
echo "  pm2 logs $APP_NAME   # live logs"
echo "  pm2 status   # process list"
echo "  ./install.sh   # run again after 'git pull' to update"
