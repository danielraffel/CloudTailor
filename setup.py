import subprocess
import json
import yaml
import os
from openai import OpenAI

# Load global variables from a file
def load_variables():
    variables = {}
    with open("variables.txt", "r") as file:
        for line in file:
            if "=" in line:
                key, value = line.split("=", 1)
                variables[key.strip()] = value.strip().strip('"')
    # Setting default values if not found in variables.txt
    variables["os_type"] = variables.get("os_type", "ubuntu-2204-lts-arm64")
    variables["server_type"] = variables.get("server_type", "e2-micro")
    return variables

# Check if variables.txt exists
if not os.path.exists("variables.txt"):
    print("variables.txt file is required to run this script.")
    exit(1)

# Load variables from variables.txt
vars = load_variables()

# Get variables
app_hostname = vars.get("app_hostname")
docker_images = vars.get("docker_images").split()
region = vars.get("region")
ssh_public_key_path = vars.get("ssh_public_key_path")
OPENAI_API_KEY = vars.get("OPENAI_API_KEY")

client = OpenAI(api_key=OPENAI_API_KEY)

# Determine the SSH username from the SSH public key file
def get_ssh_user_from_key(ssh_public_key_path):
    try:
        with open(ssh_public_key_path, 'r') as file:
            ssh_key_contents = file.read()
            # The username is typically the last part of the SSH key line
            return ssh_key_contents.strip().split()[-1]
    except Exception as e:
        print(f"Error reading SSH public key file: {e}")
        return None

# Read the SSH public key file
def read_ssh_public_key(ssh_public_key_path):
    try:
        with open(ssh_public_key_path, 'r') as file:
            return file.read().strip()
    except Exception as e:
        print(f"Error reading SSH public key file: {e}")
        return None
# Fetch project ID using Google Cloud CLI
def fetch_project_id():
# Fetch project ID using Google Cloud CLI
    result = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
    return result.stdout.strip()

# Fetch or create a Google Cloud service account key
def fetch_service_account_key():
    key_filename = "service-account-key.json"

    # Check if the service account key file already exists
    if os.path.exists(key_filename):
        print(f"{key_filename} already exists. Skipping key generation.")
        return key_filename

    # Fetch service account details
    accounts = subprocess.run(["gcloud", "iam", "service-accounts", "list", "--format=json"], capture_output=True, text=True)
    accounts_json = json.loads(accounts.stdout)

    # Look for the Compute Engine default service account
    compute_engine_service_account = None
    for account in accounts_json:
        if 'Compute Engine default service account' in account.get('displayName', ''):
            compute_engine_service_account = account["email"]
            break

    if not compute_engine_service_account:
        print("Compute Engine default service account not found.")
        return None

    # Creating a service account key
    create_key_result = subprocess.run(
        ["gcloud", "iam", "service-accounts", "keys", "create", key_filename, "--iam-account", compute_engine_service_account],
        capture_output=True, text=True
    )

    if create_key_result.returncode != 0:
        # Handle error in key creation
        print("Error creating service account key:", create_key_result.stderr)
        return None

    return key_filename

credentials_path = fetch_service_account_key()

# Format hostname to comply with GCP naming conventions
def format_hostname(hostname):
    # Format hostname to comply with GCP naming conventions
    return hostname.replace('.', '-')

# Check for or create a static IP in GCP
def check_static_ip(hostname, region):
    formatted_hostname = format_hostname(hostname)
    # Check if the static IP exists
    result = subprocess.run(["gcloud", "compute", "addresses", "list", "--filter=NAME=" + formatted_hostname + " AND region:" + region, "--format=json"], capture_output=True, text=True)
    
    if result.returncode != 0:
        # Handle error in listing IPs
        print("Error listing static IPs:", result.stderr)
        return None, None

    addresses = json.loads(result.stdout)
    for address in addresses:
        if address["name"] == formatted_hostname:
            # Return the IP address and the formatted hostname
            return address["address"], formatted_hostname

    # If no static IP, create one
    create_result = subprocess.run(["gcloud", "compute", "addresses", "create", formatted_hostname, "--region", region, "--network-tier", "STANDARD"], capture_output=True, text=True)
    if create_result.returncode != 0:
        # Handle error in creating IP
        print("Error creating static IP:", create_result.stderr)
        return None, None

    new_address_result = subprocess.run(["gcloud", "compute", "addresses", "describe", formatted_hostname, "--region", region, "--format=json"], capture_output=True, text=True)
    if new_address_result.returncode != 0:
        # Handle error in describing new IP
        print("Error describing new static IP:", new_address_result.stderr)
        return None, None

    new_address = json.loads(new_address_result.stdout)
    return new_address["address"], formatted_hostname

# Generate Terraform configuration for GCP instance
def generate_terraform_config(project_id, static_ip, credentials_path, ssh_user, ssh_public_key, os_type, server_type):
    formatted_hostname = format_hostname(app_hostname)
    ssh_metadata = f"{ssh_user}:{ssh_public_key}"

    # Terraform configuration with compute instance details
    config = f"""# Terraform configuration for setting up an instance in GCP
provider "google" {{
    project     = "{project_id}"
    region      = "{region}"
    credentials = "{credentials_path}"
}}
resource "google_compute_instance" "{formatted_hostname}" {{
    name         = "{formatted_hostname}"
    machine_type = "{server_type}"
    zone         = "{region}-a"
    boot_disk {{
        initialize_params {{
            image = "{os_type}"
            size  = 60
        }}
    }}
    network_interface {{
        network = "default"
        access_config {{
            nat_ip = "{static_ip}"
            network_tier = "STANDARD"
        }}
    }}
    metadata = {{
        "ssh-keys" = "{ssh_metadata}"
    }}
    connection {{
        type        = "ssh"
        user        = "{ssh_user}"
        private_key = file("{ssh_private_key_path}")
        host        = self.network_interface[0].access_config[0].nat_ip
    }}
    provisioner "file" {{
        source      = "setup_server.sh"
        destination = "/tmp/setup_server.sh"
    }}
    provisioner "file" {{
        source      = "setup_cloudflare.sh"
        destination = "/tmp/setup_cloudflare.sh"
    }}
    provisioner "file" {{
        source      = "docker-compose.yml"
        destination = "/tmp/docker-compose.yml"
    }}
    provisioner "file" {{
        source      = "docker-compose.service"
        destination = "/tmp/docker-compose.service"
    }}
    provisioner "file" {{
        source      = "updater.sh"
        destination = "/tmp/updater.sh"
    }}
    provisioner "remote-exec" {{
        inline = [
            "sudo mv /tmp/setup_server.sh /opt/setup_server.sh",
            "sudo chmod +x /opt/setup_server.sh",
            "sudo mv /tmp/setup_cloudflare.sh /opt/setup_cloudflare.sh",
            "sudo chmod +x /opt/setup_cloudflare.sh",
            "sudo mv /tmp/docker-compose.yml /opt/docker-compose.yml",
            "sudo mv /tmp/docker-compose.service /etc/systemd/system/docker-compose.service",
            "sudo mv /tmp/updater.sh /opt/updater.sh",
            "sudo chmod +x /opt/updater.sh",
        ]
    }}
}}

output "instance_ip" {{
    value = "{static_ip}"
}}
"""

    # Adding firewall rules for HTTP and HTTPS
    firewall_rules = f"""
resource "google_compute_firewall" "http-ingress" {{
    name    = "http-ingress"
    network = "default"

    allow {{
        protocol = "tcp"
        ports    = ["80"]
    }}

    source_ranges = ["0.0.0.0/0"]
}}

resource "google_compute_firewall" "https-ingress" {{
    name    = "https-ingress"
    network = "default"

    allow {{
        protocol = "tcp"
        ports    = ["443"]
    }}

    source_ranges = ["0.0.0.0/0"]
}}
"""
    # Append the firewall rules to the existing configuration
    config += firewall_rules

    # Write the complete configuration to the Terraform file
    with open("setup.tf", "w") as file:
        file.write(config)

# Pull Docker images as specified in variables.txt
def install_docker_images():
    for image in docker_images:
        subprocess.run(["docker", "pull", image])

# Generate Docker Compose YAML using OpenAI API based on Docker images specified in variables.txt
def generate_docker_compose_yaml(api_key, docker_images, ssh_user):
    try:
        system_message = "You are a helpful assistant designed to output a Docker Compose YAML configuration as a JSON object."
        user_message = f"Generate a Docker Compose v3 YAML configuration for services with the following Docker images: {', '.join(docker_images)}. Ensure that ports are properly configured for each service. The configuration should be compatible with docker-compose-plugin. Assume files on disk will be saved in /home/{ssh_user}/."

        response = client.chat.completions.create(
            model="gpt-4-1106-preview",
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": system_message},
                {"role": "user", "content": user_message}
            ]
        )

        # Verbose logging for debugging
        print("Response received from OpenAI API:", response)

        # Parse the JSON response
        docker_compose_json = json.loads(response.choices[0].message.content)

        # Convert JSON to YAML format
        docker_compose_yaml = yaml.dump(docker_compose_json, sort_keys=False)

        # Check if the response is complete
        if response.choices[0].finish_reason != "length":
            create_file("docker-compose.yml", docker_compose_yaml)
            return docker_compose_yaml  # Return the YAML content
        else:
            print("Error: The response was cut off due to length. Please try with a shorter prompt or increase max_tokens.")
            return None

    except json.JSONDecodeError as json_err:
        print(f"JSON Parsing Error: {json_err}")
        # Additional logging for debugging
        print("Response causing JSON Parsing Error:", response)
        return None
    except Exception as e:
        print(f"Error generating Docker Compose YAML: {e}")
        # Additional exception details
        import traceback
        traceback.print_exc()
        return None

    # Function to generate the Cloudflare setup script dynamically
def generate_cloudflare_script(docker_compose_yaml, formatted_hostname, static_ip, app_hostname):
    # Initialize the ingress entries list
    ingress_entries = []
    
    # Parse the YAML to find ports
    compose_data = yaml.safe_load(docker_compose_yaml)
    for service_name, service_details in compose_data.get('services', {}).items():
        # Check if 'ports' are defined for the service
        if 'ports' in service_details:
            for port in service_details['ports']:
                # Extract the container port
                container_port = port.split(':')[1] if ':' in port else port
                ingress_entries.append(f"echo \"    service: http://localhost:{container_port}\" >> /etc/cloudflared/config.yml")
    
    # Generate the cloudflare script using the ingress entries
    cloudflare_script = f"""#!/bin/bash
# Add cloudflare gpg key
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

# Add this repo to your apt repositories
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

# install cloudflared
sudo apt-get update && sudo apt-get install cloudflared
sudo cloudflared tunnel login
sudo cloudflared tunnel create {formatted_hostname}
sudo cloudflared tunnel route ip add {static_ip}/32 {formatted_hostname}
sudo cloudflared tunnel route dns {formatted_hostname} {app_hostname}
tunnel_id=$(sudo cloudflared tunnel info {formatted_hostname} | grep -oP 'Your tunnel \K([a-z0-9-]+)')

# Create config file
mkdir /etc/cloudflared
echo "tunnel: {formatted_hostname}" > /etc/cloudflared/config.yml
echo "credentials-file: /root/.cloudflared/$tunnel_id.json" >> /etc/cloudflared/config.yml
echo "protocol: quic" >> /etc/cloudflared/config.yml
echo "logfile: /var/log/cloudflared.log" >> /etc/cloudflared/config.yml
echo "loglevel: debug" >> /etc/cloudflared/config.yml
echo "transport-loglevel: info" >> /etc/cloudflared/config.yml
echo "ingress:" >> /etc/cloudflared/config.yml
echo "  - hostname: {app_hostname}" >> /etc/cloudflared/config.yml
"""

    # Add ingress entries
    for entry in ingress_entries:
        cloudflare_script += f"{entry}\n"

    # Add the default 404 service and additional commands
    cloudflare_script += """echo "  - service: http_status:404" >> /etc/cloudflared/config.yml
cloudflared service install
systemctl start cloudflared
systemctl status cloudflared
"""

    # Write the complete script to a file
    create_file("setup_cloudflare.sh", cloudflare_script)

# Main script execution
vars = load_variables()

# Extract variables
os_type = vars.get("os_type")
server_type = vars.get("server_type")

project_id = fetch_project_id()
credentials_path = fetch_service_account_key()
static_ip, formatted_hostname = check_static_ip(app_hostname, region)
ssh_public_key_path = vars.get("ssh_public_key_path")
ssh_private_key_path = ssh_public_key_path.rsplit('.', 1)[0]

if static_ip is None or formatted_hostname is None:
    print("Error: Unable to obtain static IP or formatted hostname.")
    exit(1)

# Extract SSH user and public key from the public key file
ssh_user = get_ssh_user_from_key(ssh_public_key_path)
ssh_public_key = read_ssh_public_key(ssh_public_key_path)

if ssh_user is None or ssh_public_key is None:
    print("Error: Unable to extract SSH user or public key from the public key file.")
    exit(1)

# Create a file with specified content
def create_file(file_name, content):
    with open(file_name, "w") as file:
        file.write(content)

# Generate setup_server.sh
docker_pull_commands = "\n".join([f"docker pull {image}" for image in docker_images])
create_file("setup_server.sh", f"""#!/bin/bash 
# Update and Install Dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
# Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update apt repositories
sudo apt-get update

# Install Docker
sudo apt-get install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker service
systemctl start docker
systemctl enable docker

# Pull Docker images
{docker_pull_commands}

# Change to the working directory
cd /opt

# Start Docker Compose
sudo docker compose up -d

# Enable Docker Compose service
systemctl enable docker-compose.service
""")

# Generate docker-compose.service
create_file("docker-compose.service", """[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt
ExecStart=docker compose -f /opt/docker-compose.yml up
ExecStop=docker compose -f /opt/docker-compose.yml down
Restart=always
RestartSec="5s"

[Install]
WantedBy=multi-user.target
""")

# Generate updater.sh
docker_pull_commands = "\n".join([f"docker pull {image}" for image in docker_images])
create_file("updater.sh", f"""#!/bin/bash
# Update the package index
sudo apt update

# Upgrade Docker and Cloudflared
sudo apt upgrade docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin cloudflared

# Pull latest docker images
{docker_pull_commands}

# Stop current setup
sudo docker compose stop

# Delete docker-containers (data is stored separately)
sudo docker compose rm

# Start Docker again
sudo docker compose -f /opt/docker-compose.yml up -d
""")

# Generate Docker Compose YAML using OpenAI and store it in docker_compose_yaml variable
docker_compose_yaml = generate_docker_compose_yaml(OPENAI_API_KEY, docker_images, ssh_user)

if docker_compose_yaml:
    # Generate Cloudflare Script updating ports based on YAML
    generate_cloudflare_script(docker_compose_yaml, formatted_hostname, static_ip, app_hostname)
else:
    print("Error: Failed to generate Docker Compose YAML.")
    exit(1)

# Generate Cloudflare Script updating ports based on YAML
generate_cloudflare_script(docker_compose_yaml, formatted_hostname, static_ip, app_hostname)

# Generate Terraform configuration
generate_terraform_config(project_id, static_ip, credentials_path, ssh_user, ssh_public_key, os_type, server_type)
