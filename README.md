# Bambu Labs Discord Bot

Discord bot for monitoring Bambu Labs 3D printers and sending status updates to Discord.

## Setup

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Configure your printers and Discord webhook in `config.yaml`:

   **Printer settings (you can add multiple printers):**
   - `name`: A friendly name for the printer (e.g., "Main Printer", "Garage Printer")
   - `ip`: Printer's IP address (find in printer settings)
   - `serial`: Printer's serial number (on the printer)
   - `access_code`: Access code from printer settings (Settings > General > LAN Access Code)
   - `ping_user_id`: (Optional) Discord user ID to ping when THIS printer finishes, fails, or pauses. Set to `null` to disable

   **Discord settings:**
   - `webhook_url`: Your Discord webhook URL (see below)
   - `update_time_interval`: Seconds between time-based updates (e.g., 3600 = 1 hour, set to `null` to disable)
   - `update_percent_interval`: Send update every X percent progress (e.g., 25 = updates at 0%, 25%, 50%, 75%, 100%, set to `null` to disable)

## Creating a Discord Webhook

1. Open Discord and go to your server
2. Go to Server Settings > Integrations > Webhooks
3. Click "New Webhook"
4. Name it (e.g., "Bambu Printer")
5. Select the channel where updates should be posted
6. Click "Copy Webhook URL"
7. Paste the URL into `config.yaml` under `discord.webhook_url`

## Getting Your Discord User ID (Optional - for Pings)

If you want to be pinged when a specific printer finishes, fails, or pauses:

1. Enable Developer Mode in Discord:
   - User Settings > App Settings > Advanced > Enable "Developer Mode"
2. Right-click your username anywhere in Discord
3. Click "Copy User ID"
4. Paste the ID into `config.yaml` under the printer's `ping_user_id`

Example - different users for different printers:
```yaml
printers:
  - name: "Tank"
    ip: 10.0.11.180
    serial: 31B8AP5A0400549
    access_code: 93d12e23
    ping_user_id: "123456789012345678"  # Ping Alice for Tank

  - name: "Gadget"
    ip: 10.0.7.76
    serial: 01P09C531901895
    access_code: 32946686
    ping_user_id: "987654321098765432"  # Ping Bob for Gadget
```

To disable pings for a printer, set it to `null`:
```yaml
printers:
  - name: "Tank"
    ping_user_id: null  # No pings for this printer
```

## Running the Monitor

### Option 1: Docker (Recommended for NAS/Server)

1. Create your `config.yaml` in the same directory as `docker-compose.yml`

2. Update the image name in `docker-compose.yml` to match your GitHub username:
   ```yaml
   image: ghcr.io/YOUR_USERNAME/chibichonk:latest
   ```

3. Start the container:
   ```bash
   docker-compose up -d
   ```

4. View logs:
   ```bash
   docker-compose logs -f
   ```

5. Stop the container:
   ```bash
   docker-compose down
   ```

The container will automatically restart if it crashes or when the system reboots.

### Option 2: Direct Python

Run the monitoring script:
```bash
python chibichonk.py
```

This will:
- Connect to all configured printers simultaneously
- Send a Discord webhook when any printer status changes (IDLE → RUNNING → FINISH, etc.)
- Send periodic updates based on time (e.g., every hour) OR progress milestones (e.g., every 25%)
- Display all updates in the console with printer names
- Each printer runs in its own thread for independent monitoring

Press Ctrl+C to stop monitoring all printers.

## Multiple Printers

The script supports monitoring multiple printers at once. Simply add more printer entries in `config.yaml`:

```yaml
printers:
  - name: "Main Printer"
    ip: 10.0.11.180
    serial: 31B8AP5A0400549
    access_code: 93d12e23

  - name: "Second Printer"
    ip: 10.0.11.181
    serial: ANOTHERSERIAL
    access_code: ANOTHERCODE
```

Each printer will:
- Monitor independently in its own thread
- Send Discord messages with its name in the title
- Show color-coded status updates

## What Gets Sent to Discord

The bot sends rich embed messages with:
- Printer name (in the title)
- Printer status (IDLE, RUNNING, PAUSE, FINISH, etc.)
- Bed temperature (current/target)
- Nozzle temperature (current/target)
- Print progress percentage
- Current layer / total layers
- Time remaining (formatted as hours and minutes)

**Color coding by status:**
- 🟢 Green: RUNNING, PREPARE (actively printing)
- 🟠 Orange: PAUSE (paused)
- 🔴 Red: FAILED (error/failed print)
- 🔵 Blue: FINISH (completed successfully)
- ⚪ Gray: IDLE (idle/ready)
- 🟣 Purple: Unknown states

## Finding Your Printer Details

- **IP Address**: Check your printer's network settings or your router's DHCP client list
- **Serial Number**: Found on the printer itself or in the printer settings
- **Access Code**: Go to printer settings > General > LAN Access Code (you may need to enable LAN mode first)

## Requirements

- Python 3.10 or higher (for local setup)
- Docker (for containerized deployment)
- Bambu Labs printer with LAN mode enabled (LAN Only Mode is NOT required)

## Deployment to Synology NAS

1. **Enable SSH** on your Synology NAS (Control Panel > Terminal & SNMP > Enable SSH)

2. **Install Container Manager** (formerly Docker) from Package Center

3. **SSH into your NAS** and create a directory:
   ```bash
   mkdir -p /volume1/docker/chibichonk
   cd /volume1/docker/chibichonk
   ```

4. **Copy your `config.yaml`** to this directory

5. **Create `docker-compose.yml`**:
   ```bash
   wget https://raw.githubusercontent.com/YOUR_USERNAME/chibichonk/main/docker-compose.yml
   ```

   Or copy the file manually and update the image name to match your GitHub username.

6. **Start the container**:
   ```bash
   docker-compose up -d
   ```

7. **View logs**:
   ```bash
   docker-compose logs -f chibichonk
   ```

The container will automatically start when your NAS boots up.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
