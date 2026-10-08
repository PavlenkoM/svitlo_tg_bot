# svitlo_tg_bot

Telegram bot that watches whether the city electricity grid is on and notifies all chats that started the bot when the state changes.

Two ways to detect electricity (set `check-method` in `config/config.yaml`):

| Method | How it works | When to use |
|---|---|---|
| `ping` | Pings a local device that is powered only from the city grid | No inverter / UPS in the house |
| `deye-local` | Reads grid voltage from a Deye inverter via its Solarman WiFi logger on the local network (TCP port 8899) | Inverter + battery keep everything powered during outages |

## Configuration

```bash
cp config/example_config.yaml config/config.yaml
```

Edit `config/config.yaml`:
- `telegram-token` — token from [@BotFather](https://t.me/BotFather)
- `check-method` — `ping` or `deye-local`
- for `ping`: `ip-address` of the device to ping
- for `deye-local`: `logger-ip` and `logger-serial` (see below)

All options are described in `config/example_config.yaml`.

### Deye inverter (`deye-local`)

The bot reads the inverter through its WiFi logger stick. It must run in the same local network as the logger.

1. Reserve a fixed IP for the logger in your router (DHCP reservation).
2. Check that the logger accepts local connections:
   ```bash
   nc -vz <logger-ip> 8899
   ```
3. Find the logger serial number (the logger stick, **not** the inverter):
   ```bash
   python3 deyeProbe.py --discover
   ```
   If nothing is found, take it from the logger sticker or from the Deye Cloud app ("Datalogger SN").
4. Check the readings:
   ```bash
   python3 deyeProbe.py <logger-ip> <logger-serial>
   ```
   With the grid on you should see about 230 V on each phase and about 50 Hz.
5. Put `logger-ip` and `logger-serial` under `deye-local` in `config/config.yaml` and set `check-method: 'deye-local'`.

Register map is for Deye 3-phase low-voltage hybrid inverters (SUN-*K-SG04LP3 / SG05LP3).

## Running on Raspberry Pi with pm2

### Quick install

```bash
git clone https://github.com/PavlenkoM/svitlo_tg_bot.git
cd svitlo_tg_bot
./install.sh
```

The script:
- installs missing system packages (`python3`, `python3-venv`, `git`), Node.js and pm2
- creates `venv/` and installs Python dependencies
- if `config/config.yaml` does not exist, asks for the Telegram token and check method, and for `deye-local` finds the inverter logger in the local network
- checks the inverter connection (`deye-local` only)
- starts the bot with pm2 (an existing pm2 process that runs this bot is reused, not duplicated) and enables autostart after reboot

It is safe to run again: to update, run `git pull && ./install.sh`. Use `APP_NAME=my-name ./install.sh` for a custom pm2 process name on the first install.

### Manual install

#### 1. Install system packages

```bash
sudo apt update
sudo apt install -y git python3 python3-venv
```

Install Node.js and pm2 if they are not installed yet:

```bash
sudo apt install -y nodejs npm
sudo npm install -g pm2
```

#### 2. Get the code and install dependencies

```bash
git clone https://github.com/PavlenkoM/svitlo_tg_bot.git
cd svitlo_tg_bot

python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

A virtual environment is needed because Raspberry Pi OS (Bookworm and newer) does not allow `pip install` into the system Python.

#### 3. Configure

```bash
cp config/example_config.yaml config/config.yaml
nano config/config.yaml
```

For `deye-local`, run the checks from [Deye inverter](#deye-inverter-deye-local) using the venv Python, for example:

```bash
./venv/bin/python deyeProbe.py --discover
./venv/bin/python deyeProbe.py <logger-ip> <logger-serial>
```

#### 4. Start with pm2

```bash
pm2 start main.py --name svitlo-bot --interpreter ./venv/bin/python --interpreter-args="-u"
```

`-u` turns off Python output buffering, otherwise `pm2 logs` shows the bot output with a delay.

#### 5. Start automatically after reboot

```bash
pm2 startup   # prints a command — run it once
pm2 save
```

### Useful commands

```bash
pm2 status                 # list processes
pm2 logs svitlo-bot        # live logs
pm2 restart svitlo-bot     # restart
pm2 stop svitlo-bot        # stop
```

### Updating

```bash
cd svitlo_tg_bot
git pull
./venv/bin/pip install -r requirements.txt
pm2 restart svitlo-bot
```

If the bot is already registered in pm2 with another Python interpreter (for example from an older setup), re-create it so it uses the venv:

```bash
pm2 delete svitlo-bot
pm2 start main.py --name svitlo-bot --interpreter ./venv/bin/python --interpreter-args="-u"
pm2 save
```
