#!/usr/bin/env python3
"""
Chibichonk - Bambu Labs 3D Printer Discord Monitor

Monitor script to watch for Bambu Labs printer status changes and send updates to Discord.

Vibe coded.

Copyright (c) 2025 Mark Smith

Licensed under the MIT License - see LICENSE file for details
"""
import time
import yaml
from datetime import datetime
import requests
import bambulabs_api as bl
import threading

# Load configuration from config.yaml
# Support both local and Docker mounted config
import os
config_path = os.getenv('CONFIG_PATH', 'config.yaml')
if not os.path.exists(config_path) and os.path.exists('config/config.yaml'):
    config_path = 'config/config.yaml'

with open(config_path, 'r') as f:
    config = yaml.safe_load(f)

# Get Discord details from config
WEBHOOK_URL = config['discord']['webhook_url']
UPDATE_TIME_INTERVAL = config['discord'].get('update_time_interval', 3600)  # Default 1 hour
UPDATE_PERCENT_INTERVAL = config['discord'].get('update_percent_interval', 25)  # Default 25%

def get_timestamp():
    """Get current timestamp for logging."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def get_printer_data(printer, printer_name=None, debug=False):
    """Gather all available printer data."""
    data = {
        'status': None,
        'bed_temp': None,
        'nozzle_temp': None,
        'target_bed_temp': None,
        'target_nozzle_temp': None,
        'progress': None,
        'current_layer': None,
        'total_layers': None,
        'remaining_time': None,
        'print_speed': None,
        'fan_speed': None,
        'filename': None,
    }

    try:
        # Access the MQTT data dictionary
        mqtt_data = printer.mqtt_client._data.get('print', {})

        if debug and printer_name:
            print(f"\n[DEBUG] [{printer_name}] Full MQTT _data structure:")
            import json
            try:
                print(json.dumps(printer.mqtt_client._data, indent=2, default=str))
            except Exception as e:
                print(f"  Error dumping JSON: {e}")
                print(f"  Raw data: {printer.mqtt_client._data}")
            print(f"\n[DEBUG] [{printer_name}] Available MQTT print data keys:")
            print(f"  {list(mqtt_data.keys())}")
            print(f"\n[DEBUG] [{printer_name}] Key values:")
            for key in ['gcode_state', 'bed_temper', 'bed_target_temper', 'nozzle_temper',
                       'nozzle_target_temper', 'mc_percent', 'layer_num', 'total_layer_num',
                       'mc_remaining_time', 'spd_mag', 'cooling_fan_speed', 'subtask_name']:
                print(f"  {key}: {mqtt_data.get(key)}")
            print()

        # Get status
        data['status'] = mqtt_data.get('gcode_state')

        # Get temperatures
        data['bed_temp'] = mqtt_data.get('bed_temper')
        data['target_bed_temp'] = mqtt_data.get('bed_target_temper')
        data['nozzle_temp'] = mqtt_data.get('nozzle_temper')
        data['target_nozzle_temp'] = mqtt_data.get('nozzle_target_temper')

        # Get print progress
        data['progress'] = mqtt_data.get('mc_percent')
        data['current_layer'] = mqtt_data.get('layer_num')
        data['total_layers'] = mqtt_data.get('total_layer_num')

        # Get remaining time (in minutes)
        data['remaining_time'] = mqtt_data.get('mc_remaining_time')

        # Get speed (percentage)
        data['print_speed'] = mqtt_data.get('spd_mag')

        # Get fan speed (convert string to int)
        fan_speed = mqtt_data.get('cooling_fan_speed')
        if fan_speed:
            data['fan_speed'] = int(fan_speed) if isinstance(fan_speed, str) else fan_speed

        # Get filename
        data['filename'] = mqtt_data.get('subtask_name')

    except Exception as e:
        print(f"Error getting printer data: {e}")

    return data

def send_discord_webhook(data, printer_name, ping_user_id=None, is_state_change=False):
    """Send printer data to Discord webhook."""
    if WEBHOOK_URL == "YOUR_DISCORD_WEBHOOK_URL_HERE":
        return  # Skip if webhook not configured

    # Skip if we have absolutely no useful data
    if (data['status'] is None and data['bed_temp'] is None and
        data['nozzle_temp'] is None and data['progress'] is None):
        return  # No data to send

    # Determine color based on printer state
    status = data['status']
    if status in ['RUNNING', 'PREPARE']:
        color = 0x00ff00  # Green - actively printing
    elif status in ['PAUSE']:
        color = 0xffa500  # Orange - paused
    elif status in ['FAILED']:
        color = 0xff0000  # Red - failed
    elif status in ['FINISH']:
        color = 0x3498db  # Blue - completed successfully
    elif status in ['IDLE']:
        color = 0x95a5a6  # Gray - idle
    else:
        # Unknown or no status - use yellow/amber for partial data
        color = 0xffbf00  # Amber - partial/unknown state

    # Build embed fields
    fields = []

    # Status field
    if data['status']:
        fields.append({
            "name": "Status",
            "value": data['status'],
            "inline": True
        })
    elif data['bed_temp'] is not None or data['nozzle_temp'] is not None:
        # If we have temps but no status, show "Active"
        fields.append({
            "name": "Status",
            "value": "Active (partial data)",
            "inline": True
        })

    # Temperature fields
    if data['bed_temp'] is not None:
        temp_text = f"{data['bed_temp']}°C"
        if data['target_bed_temp'] is not None:
            temp_text += f" / {data['target_bed_temp']}°C"
        fields.append({
            "name": "Bed Temperature",
            "value": temp_text,
            "inline": True
        })

    if data['nozzle_temp'] is not None:
        temp_text = f"{data['nozzle_temp']}°C"
        if data['target_nozzle_temp'] is not None:
            temp_text += f" / {data['target_nozzle_temp']}°C"
        fields.append({
            "name": "Nozzle Temperature",
            "value": temp_text,
            "inline": True
        })

    # Filename (as code block to prevent markdown interpretation)
    if data['filename']:
        fields.append({
            "name": "File",
            "value": f"`{data['filename']}`",
            "inline": False
        })

    # Print progress
    if data['progress'] is not None:
        fields.append({
            "name": "Progress",
            "value": f"{data['progress']}%",
            "inline": True
        })

    if data['current_layer'] is not None and data['total_layers'] is not None:
        fields.append({
            "name": "Layer",
            "value": f"{data['current_layer']} / {data['total_layers']}",
            "inline": True
        })

    if data['remaining_time'] is not None:
        # Convert minutes to hours and minutes for better readability
        hours = data['remaining_time'] // 60
        minutes = data['remaining_time'] % 60
        if hours > 0:
            time_str = f"{hours}h {minutes}m"
        else:
            time_str = f"{minutes}m"
        fields.append({
            "name": "Time Remaining",
            "value": time_str,
            "inline": True
        })

    if data['print_speed'] is not None:
        fields.append({
            "name": "Print Speed",
            "value": f"{data['print_speed']}%",
            "inline": True
        })

    if data['fan_speed'] is not None:
        fields.append({
            "name": "Fan Speed",
            "value": f"{data['fan_speed']}%",
            "inline": True
        })

    # Create embed
    embed = {
        "title": f"🖨️ {printer_name} - Status Change" if is_state_change else f"🖨️ {printer_name} - Update",
        "color": color,
        "fields": fields,
        "timestamp": datetime.utcnow().isoformat()
    }

    # Check if we should ping a user (only on state changes to final states)
    content = None
    if is_state_change and ping_user_id and status in ['FINISH', 'FAILED', 'PAUSE']:
        content = f"<@{ping_user_id}>"

    payload = {
        "embeds": [embed]
    }

    if content:
        payload["content"] = content

    try:
        response = requests.post(WEBHOOK_URL, json=payload)
        response.raise_for_status()
        print(f"[{get_timestamp()}] Webhook sent successfully")
    except Exception as e:
        print(f"[{get_timestamp()}] Error sending webhook: {e}")

def print_status_info(data, printer_name):
    """Print detailed status information to console."""
    print(f"\n[{get_timestamp()}] [{printer_name}] Status: {data['status']}")
    print("-" * 50)

    if data['filename']:
        print(f"  File: {data['filename']}")

    if data['bed_temp'] is not None:
        print(f"  Bed Temperature: {data['bed_temp']}°C / {data['target_bed_temp']}°C")
    if data['nozzle_temp'] is not None:
        print(f"  Nozzle Temperature: {data['nozzle_temp']}°C / {data['target_nozzle_temp']}°C")

    if data['progress'] is not None:
        print(f"  Print progress: {data['progress']}%")
    if data['current_layer'] is not None and data['total_layers'] is not None:
        print(f"  Layer: {data['current_layer']}/{data['total_layers']}")
    if data['remaining_time'] is not None:
        hours = data['remaining_time'] // 60
        minutes = data['remaining_time'] % 60
        if hours > 0:
            print(f"  Time Remaining: {hours}h {minutes}m")
        else:
            print(f"  Time Remaining: {minutes}m")
    if data['print_speed'] is not None:
        print(f"  Print Speed: {data['print_speed']}%")
    if data['fan_speed'] is not None:
        print(f"  Fan Speed: {data['fan_speed']}%")

    print("-" * 50)

def monitor_printer(printer_config, stop_event):
    """Monitor a single printer in its own thread."""
    printer_name = printer_config['name']
    printer_ip = printer_config['ip']
    printer_serial = str(printer_config['serial'])  # Ensure string
    access_code = str(printer_config['access_code'])  # Ensure string
    ping_user_id = printer_config.get('ping_user_id', None)  # Discord user ID to ping

    print(f"[{get_timestamp()}] [{printer_name}] Connecting to printer at {printer_ip}...")

    # Create a new instance of the API
    printer = bl.Printer(printer_ip, access_code, printer_serial)

    try:
        # Connect to the printer (MQTT only, no camera)
        printer.mqtt_start()
        print(f"[{get_timestamp()}] [{printer_name}] Connected! Waiting for printer data...")

        # Wait for data to arrive (with timeout)
        # First, try to trigger a full status push
        try:
            printer.mqtt_client.publish("pushall")
        except Exception:
            pass  # Not all API versions may support this

        max_wait = 30  # seconds
        wait_interval = 0.5
        waited = 0
        data = None

        while waited < max_wait:
            time.sleep(wait_interval)
            waited += wait_interval
            data = get_printer_data(printer, printer_name)

            # Check if we have key data fields (status or at least temps and progress)
            has_status = data['status'] is not None
            has_temps = data['bed_temp'] is not None and data['nozzle_temp'] is not None

            if has_status or (has_temps and waited > 5):
                # Either we have status, or we have temps and waited at least 5 seconds
                print(f"[{get_timestamp()}] [{printer_name}] Data received after {waited:.1f}s")
                break

        if data is None or (data['status'] is None and data['bed_temp'] is None):
            print(f"[{get_timestamp()}] [{printer_name}] Warning: No data received after {max_wait}s, continuing anyway...")

        # Get initial status (set debug=True to see full MQTT data)
        data = get_printer_data(printer, printer_name, debug=False)
        last_status = data['status']
        print_status_info(data, printer_name)
        send_discord_webhook(data, printer_name, ping_user_id, is_state_change=True)

        last_update_time = time.time()
        last_progress = data['progress'] if data['progress'] is not None else 0
        last_progress_milestone = (last_progress // UPDATE_PERCENT_INTERVAL) * UPDATE_PERCENT_INTERVAL

        # Monitor loop
        while not stop_event.is_set():
            time.sleep(0.1)  # Check frequently but send updates at interval

            current_time = time.time()
            data = get_printer_data(printer, printer_name)
            current_status = data['status']
            current_progress = data['progress'] if data['progress'] is not None else 0

            # Check if status changed
            if current_status != last_status:
                print_status_info(data, printer_name)
                send_discord_webhook(data, printer_name, ping_user_id, is_state_change=True)
                last_status = current_status
                last_update_time = current_time  # Reset update timer on state change
                last_progress_milestone = (current_progress // UPDATE_PERCENT_INTERVAL) * UPDATE_PERCENT_INTERVAL

            else:
                # Check if we should send a periodic update
                time_passed = current_time - last_update_time >= UPDATE_TIME_INTERVAL

                # Check if progress crossed a milestone (e.g., 0->25, 25->50, etc.)
                current_milestone = (current_progress // UPDATE_PERCENT_INTERVAL) * UPDATE_PERCENT_INTERVAL
                progress_milestone_crossed = current_milestone > last_progress_milestone

                if time_passed or progress_milestone_crossed:
                    reason = []
                    if time_passed:
                        reason.append(f"time ({UPDATE_TIME_INTERVAL}s elapsed)")
                    if progress_milestone_crossed:
                        reason.append(f"progress ({last_progress_milestone}% -> {current_milestone}%)")

                    print(f"[{get_timestamp()}] [{printer_name}] Periodic update ({', '.join(reason)})")
                    send_discord_webhook(data, printer_name, ping_user_id, is_state_change=False)
                    last_update_time = current_time
                    last_progress_milestone = current_milestone

    except Exception as e:
        print(f"[{get_timestamp()}] [{printer_name}] Error: {e}")
    finally:
        # Disconnect from the printer
        print(f"[{get_timestamp()}] [{printer_name}] Disconnecting...")
        printer.mqtt_stop()
        print(f"[{get_timestamp()}] [{printer_name}] Disconnected.")

def main():
    # Get list of printers from config
    printers = config.get('printers', [])

    if not printers:
        print("Error: No printers configured in config.yaml")
        return

    print(f"[{get_timestamp()}] Starting monitoring for {len(printers)} printer(s)")
    print(f"[{get_timestamp()}] Update intervals:")
    print(f"  Time: every {UPDATE_TIME_INTERVAL} seconds ({UPDATE_TIME_INTERVAL/3600:.1f} hours)")
    print(f"  Progress: every {UPDATE_PERCENT_INTERVAL}%")
    print("Press Ctrl+C to stop monitoring")
    print()

    # Create stop event for graceful shutdown
    stop_event = threading.Event()

    # Start a thread for each printer
    threads = []
    for printer_config in printers:
        thread = threading.Thread(
            target=monitor_printer,
            args=(printer_config, stop_event),
            daemon=True
        )
        thread.start()
        threads.append(thread)

    try:
        # Wait for keyboard interrupt
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print(f"\n[{get_timestamp()}] Monitoring stopped by user")
        print("Shutting down all printer monitors...")
        stop_event.set()

        # Wait for all threads to finish
        for thread in threads:
            thread.join(timeout=5)

        print("All monitors stopped.")

if __name__ == '__main__':
    main()
