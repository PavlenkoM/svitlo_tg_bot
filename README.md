# svitlo_tg_bot

Telegram bot that watches whether the city electricity grid is on and notifies all chats that started the bot when the state changes.

Electricity is detected by grid voltage reported by a Deye inverter. The bot reads it from the inverter's Solarman WiFi logger over the local network (TCP port 8899), so the bot must run in the same network as the logger. Pinging a device does not work with an inverter + battery, because everything stays powered during outages.

## Notifications

A message is sent to subscribed chats when the grid state changes:

| State | Meaning |
|---|---|
| 💡 ON | all 3 phases have electricity |
| ⚠️ PARTIAL | 1 or 2 phases have electricity — the inverter disconnects from the grid and works from the battery |
| 🌚 OFF | no electricity on any phase |

A phase has electricity when its voltage is at least `min-grid-voltage`. With `/phases_on` a message also shows every phase voltage: 🟢 220–250 V, 🟡 too low or too high, 🔴 no electricity (hidden by default).

While the state is ⚠️ PARTIAL, a message is also sent when any phase moves to or from 🔴 (for example 🟡 → 🔴). Changes between 🟢 and 🟡, and voltage changes inside the same zone (195 V → 196 V), do not send messages.

```
⚠️ - PARTIAL
🟡 200 V | 🟡 200 V | 🔴 0 V
```

**PARTIAL messages are optional.** By default a chat gets only 💡 ON / 🌚 OFF: PARTIAL counts as ON, so OFF is sent only when all phases have no electricity. A chat can turn PARTIAL messages on with `/partial_on` and off with `/partial_off`; the choice is saved.

## Bot commands

| Command | Action |
|---|---|
| `/start` | Subscribe the chat to notifications (also works again after `/stop`) |
| `/stop` | Unsubscribe |
| `/partial_on` | Also get ⚠️ PARTIAL messages |
| `/partial_off` | Get only 💡 ON / 🌚 OFF (default) |
| `/phases_on` | Show phase voltages in messages |
| `/phases_off` | Hide phase voltages: messages show only the state, for example `💡 - ON` (default) |

**Admin command.** `/status` replies with a fresh reading from the inverter: state, phase voltages, frequency, grid relay, grid power, battery and the time of the last state change. It works only for Telegram user ids listed in `admin-ids` in `config/config.yaml`, and only in a private chat with the bot. Other users get no reply and don't see the command in the menu.

```yaml
admin-ids: [123456789]
```

Your user id is the id of your private chat in `storage/chat_ids.db` after you send `/start`. Restart the bot after changing `admin-ids`.

Chats that block the bot or remove it from a group are unsubscribed automatically. Subscribers are stored in the SQLite database `storage/chat_ids.db` (chat id, username, first and last name, PARTIAL and phases settings). An old `storage/chat_ids.csv` is imported automatically on the first start and renamed to `chat_ids.csv.migrated`.

To look at subscribers on the Pi:

```bash
sqlite3 storage/chat_ids.db 'SELECT * FROM chats'
```

(`sudo apt install sqlite3` if the command is missing.) Back up `storage/chat_ids.db` together with `config/config.yaml`.

## Configuration

```bash
cp config/example_config.yaml config/config.yaml
```

Edit `config/config.yaml`:
- `telegram-token` — token from [@BotFather](https://t.me/BotFather)
- `deye-local` → `logger-ip` and `logger-serial` (see below)

All options are described in `config/example_config.yaml`.

### Deye inverter logger

1. Reserve a fixed IP for the logger in your router (DHCP reservation).
2. Check that the logger accepts local connections:
   ```bash
   nc -vz <logger-ip> 8899
   ```
3. Find the logger serial number (the logger stick, **not** the inverter):
   ```bash
   python3 deyeProbe.py --discover
   ```
   Some logger firmwares ignore discovery. Then read the serial directly from the logger by its IP:
   ```bash
   python3 deyeProbe.py --find-serial <logger-ip>
   ```
   It is also on the logger sticker.
4. Check the readings:
   ```bash
   python3 deyeProbe.py <logger-ip> <logger-serial>
   ```
   With the grid on you should see about 230 V on each phase and about 50 Hz.
5. Put `logger-ip` and `logger-serial` under `deye-local` in `config/config.yaml`.

Register map is for Deye 3-phase low-voltage hybrid inverters (SUN-*K-SG04LP3 / SG05LP3).

### Apple Home (HomeKit)

Optionally the bot also shows the grid state in the Apple Home app. It appears as a bridge (default name `Svitlo`) with two contact sensors:

| Sensor | Closed | Open |
|---|---|---|
| Grid | 💡 ON or ⚠️ PARTIAL | 🌚 OFF |
| All phases | 💡 ON | ⚠️ PARTIAL or 🌚 OFF |

The Grid sensor also shows the inverter battery level (low at 20% or less). Both sensors show a fault while the inverter does not respond, and the Home app shows "No Response" when the bot is not running. Phase voltages are not shown: HomeKit has no such sensor type.

To turn it on, add to `config/config.yaml` (all options in `config/example_config.yaml`) and restart the bot:

```yaml
homekit:
  name: 'Svitlo'
```

Then in the Home app: **+** → **Add Accessory** → scan the QR code or enter the setup code from `pm2 logs svitlo-bot`. The phone must be in the same network as the bot. In the sensor settings you can turn on **Notifications** to get an alert when the state changes, and use the sensors in automations. Notifications outside home need a home hub (Apple TV or HomePod).

The pairing is saved in `storage/homekit.state`: back it up together with `config/config.yaml`. Without it the bridge must be removed from the Home app and added again.

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
- if `config/config.yaml` does not exist, asks for the Telegram token and the logger IP, and finds the logger serial automatically
- checks the inverter connection
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

Run the checks from [Deye inverter logger](#deye-inverter-logger) using the venv Python, for example:

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
