import requests
import json
from tabulate import tabulate
from collections import defaultdict
import argparse

# API URLs
VOICE_SERVER_API = "https://routing-svc-lbe.plivops.com/Manage/VoiceServer/"
CHANNEL_COUNT_API = "https://routing-svc-lbe.plivops.com/Manage/ChannelCount/"

# Authorization header
headers = {
    'Authorization': 'Basic UERTR0RTNzY4NzZRM0pRR0VBOmY5UDZyWmk4RThSY2hNNmdaNW05ZGhiZ013TmNBVmxJSkVZa3VJNDU='
}

# Map abbreviations to full category names
category_map = {
    "ms": "media_server",
    "wms": "webrtc_server",
}

def fetch_data():
    """Fetches data from both APIs and returns them as dictionaries."""
    try:
        # Fetch channel data
        channel_response = requests.get(CHANNEL_COUNT_API, headers=headers)
        channel_response.raise_for_status()
        channel_data = channel_response.json().get('response', {})

        # Parse channel data into a dictionary
        channel_info = {
            hostname: {
                "channel_count": data.get('channel_count', 'N/A'),
                "cpu_usage": data.get('cpu_usage', 'N/A'),
                "memory_usage": data.get('memory_usage', 'N/A')
            }
            for hostname, data in channel_data.items()
        }

        # Fetch server data
        voice_response = requests.get(VOICE_SERVER_API, headers=headers)
        voice_response.raise_for_status()
        voice_servers = voice_response.json().get('response', [])

        return channel_info, voice_servers

    except requests.exceptions.RequestException as e:
        print(f"Error fetching data: {e}")
        return {}, []

def display_servers(region=None, categories=None):
    """Displays the servers by region and categories, grouped, sorted, and color-coded by channel count."""
    if categories is None:
        categories = ["media_server", "webrtc_server"]

    # Fetch data from both APIs only once
    channel_data, servers = fetch_data()

    if not servers:
        print("No server data available.")
        return

    for category in categories:
        servers_by_region = defaultdict(lambda: {'enabled': [], 'disabled': []})

        for server in servers:
            # Extract category and region directly from tags
            server_region = server.get('tags', {}).get('region', 'Unknown')
            server_category = server.get('tags', {}).get('category', 'Unknown')
            hostname = server.get('hostname')
            enabled_status = server.get('enabled', False)

            # Apply filters
            if (category and server_category != category) or (region and server_region != region):
                continue

            # Get server stats
            data = channel_data.get(hostname, {"channel_count": "N/A", "cpu_usage": "N/A", "memory_usage": "N/A"})
            channel_count = data["channel_count"]
            cpu_usage = data["cpu_usage"]
            memory_usage = data["memory_usage"]

            # Create entry with color coding
            server_entry = (
                f"\033[0;32m{hostname}\033[0m" if enabled_status else f"\033[0;31m{hostname}\033[0m",
                channel_count,
                cpu_usage,
                memory_usage
            )

            # Append to the correct list based on enabled status
            if enabled_status:
                servers_by_region[server_region]['enabled'].append(server_entry)
            else:
                servers_by_region[server_region]['disabled'].append(server_entry)

        # Display each region's servers grouped by channel count
        print(f"\nCategory: {category}, Region: {region or 'All'}")
        print("-----------------------------------------------------")

        for server_region, server_data in servers_by_region.items():
            enabled_count = len(server_data['enabled'])
            disabled_count = len(server_data['disabled'])

            # Calculate total and average calls for enabled servers
            total_enabled_calls = sum(int(server[1]) for server in server_data['enabled'] if server[1] != "N/A")
            average_enabled_calls = total_enabled_calls / enabled_count if enabled_count else 0

            print(f"\nRegion: {server_region}")

            # Display enabled servers with count, total calls, and average calls
            if server_data['enabled']:
                print(f"\033[0;32mEnabled Servers ({enabled_count}), Total Calls ({total_enabled_calls}), Average Calls ({average_enabled_calls:.2f}):\033[0m")
                print(tabulate(
                    server_data['enabled'],
                    headers=["Hostname", "Channel Count", "CPU Usage (%)", "Memory Usage (%)"],
                    tablefmt="grid"
                ))
            else:
                print(f"\033[0;32mNo enabled servers found for region '{server_region}' in category '{category}'.\033[0m")

            # Calculate total and average calls for disabled servers
            total_disabled_calls = sum(int(server[1]) for server in server_data['disabled'] if server[1] != "N/A")
            average_disabled_calls = total_disabled_calls / disabled_count if disabled_count else 0

            # Display disabled servers with count, total calls, and average calls
            if server_data['disabled']:
                print(f"\033[0;31mDisabled Servers ({disabled_count}), Total Calls ({total_disabled_calls}), Average Calls ({average_disabled_calls:.2f}):\033[0m")
                print(tabulate(
                    server_data['disabled'],
                    headers=["Hostname", "Channel Count", "CPU Usage (%)", "Memory Usage (%)"],
                    tablefmt="grid"
                ))
            else:
                print(f"\033[0;31mNo disabled servers found for region '{server_region}' in category '{category}'.\033[0m")

if __name__ == "__main__":
    # Set up argument parsing
    parser = argparse.ArgumentParser(description="Display server status.")
    parser.add_argument('region', nargs='?', default=None, help="AWS region (leave blank for all regions)")
    parser.add_argument('category', nargs='?', default=None, help="Server category (ms for media_server, wms for webrtc_server, or leave blank for both)")

    args = parser.parse_args()

    # Map the category argument to the full category name
    categories = [category_map.get(args.category, args.category)] if args.category else ["media_server", "webrtc_server"]

    # Display the server status based on the provided arguments
    display_servers(args.region, categories)
