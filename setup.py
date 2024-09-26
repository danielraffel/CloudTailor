import subprocess
import json
import yaml
import os
import shutil
import openai  # Corrected import
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
docker_images = vars.get("docker_images", "").split()
compose_file_path = vars.get("compose_file_path")
dockerfile_path = vars.get("dockerfile_path")
region = vars.get("region")
ssh_public_key_path = vars.get("ssh_public_key_path")
OPENAI_API_KEY = vars.get("OPENAI_API_KEY")
ssh_private_key_path = vars.get("ssh_private_key_path")

# Create a directory for the app_hostname
app_dir = app_hostname.replace('.', '-')  # Replace dots with hyphens for folder name
os.makedirs(app_dir, exist_ok=True)  # Create the directory if it doesn't exist

# After loading variables from variables.txt
if dockerfile_path:
    if os.path.exists(dockerfile_path):
        shutil.copy2(dockerfile_path, os.path.join(app_dir, "Dockerfile"))
        print(f"Copied Dockerfile from {dockerfile_path} to {app_dir}.")
    else:
        print(f"Warning: Dockerfile not found at {dockerfile_path}. It will not be included in the deployment.")

# Fetch or create a Google Cloud service account key
def fetch_service_account_key():
    key_filename = os.path.join(app_dir, "service-account-key.json")  # Save in app_dir
    parent_key_filename = os.path.join(os.path.dirname(app_dir), "service-account-key.json")  # Check in parent directory

    # Check if the service account key file already exists in the app_dir
    if os.path.exists(key_filename):
        print(f"{key_filename} already exists. Skipping key generation.")
        return key_filename

    # Check if the service account key file exists in the parent directory
    if os.path.exists(parent_key_filename):
        print(f"Found service account key in parent directory: {parent_key_filename}. Copying to {app_dir}.")
        shutil.copy(parent_key_filename, key_filename)
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

# Now you can safely call fetch_service_account_key
credentials_path = fetch_service_account_key()

openai.api_key = OPENAI_API_KEY  # Corrected the OpenAI client initialization

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
    result = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
    return result.stdout.strip()

# Format hostname to comply with GCP naming conventions
def format_hostname(hostname):
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
def generate_terraform_config(project_id, static_ip, credentials_path, ssh_user, ssh_public_key, os_type, server_type, dockerfile_path, compose_file_path):
    formatted_hostname = format_hostname(app_hostname)
    ssh_metadata = f"{ssh_user}:{ssh_public_key}"

    # Start the Terraform configuration
    config = f"""# Terraform configuration for setting up an instance in GCP
provider "google" {{
    project     = "{project_id}"
    region      = "{region}"
    credentials = "{credentials_filename}"
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
        source      = "docker-compose.service"
        destination = "/tmp/docker-compose.service"
    }}
    provisioner "file" {{
        source      = "updater.sh"
        destination = "/tmp/updater.sh"
    }}
"""

    # Conditional inclusion based on compose_file_path and dockerfile_path
    # Include the Docker Compose file if compose_file_path is provided or dockerfile_path is not provided
    if compose_file_path or not dockerfile_path:
        config += f"""
    provisioner "file" {{
        source      = "docker-compose.yml"
        destination = "/tmp/docker-compose.yml"
    }}
"""

    # Include the Dockerfile if dockerfile_path is provided
    if dockerfile_path:
        config += f"""
    provisioner "file" {{
        source      = "Dockerfile"
        destination = "/tmp/Dockerfile"
    }}
"""

    # Start remote-exec block
    config += f"""
    provisioner "remote-exec" {{
        inline = [
            "sudo mv /tmp/setup_server.sh /opt/setup_server.sh",
            "sudo chmod +x /opt/setup_server.sh",
            "sudo mv /tmp/setup_cloudflare.sh /opt/setup_cloudflare.sh",
            "sudo chmod +x /opt/setup_cloudflare.sh",
            "sudo mv /tmp/docker-compose.service /etc/systemd/system/docker-compose.service",
            "sudo chown root:root /etc/systemd/system/docker-compose.service",
            "sudo chmod 644 /etc/systemd/system/docker-compose.service",
            "sudo mv /tmp/updater.sh /opt/updater.sh",
            "sudo chmod +x /opt/updater.sh",
"""

    # Conditionally move Docker Compose file
    if compose_file_path or not dockerfile_path:
        config += f"""
            "sudo mv /tmp/docker-compose.yml /opt/docker-compose.yml",
"""

    # Conditionally move Dockerfile
    if dockerfile_path:
        config += f"""
            "sudo mv /tmp/Dockerfile /opt/Dockerfile",
"""

    # Continue with the rest of the commands
    config += f"""
            "echo pwd"
        ]
    }}
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

    # Output the instance IP
    config += f"""
output "instance_ip" {{
    value = "{static_ip}"
}}
"""

    # Write the complete configuration to the Terraform file in the app directory
    with open(os.path.join(app_dir, "setup.tf"), "w") as file:
        file.write(config)

# Pull Docker images as specified in variables.txt
def install_docker_images():
    for image in docker_images:
        subprocess.run(["docker", "pull", image])

# Function to copy local Docker Compose file
def copy_compose_file(source_path):
    destination_path = os.path.join(app_dir, "docker-compose.yml")  # Updated path
    shutil.copy2(source_path, destination_path)
    print(f"Copied Docker Compose file from {source_path} to {destination_path}")

# Generate Docker Compose YAML using OpenAI API or use the provided file
def generate_docker_compose_yaml(api_key, docker_images, ssh_user, compose_file_path):
    if compose_file_path:
        # If a compose file path is provided, copy it
        copy_compose_file(compose_file_path)
        with open(os.path.join(app_dir, "docker-compose.yml"), "r") as file:  # Updated path
            return file.read()
    elif docker_images:
        try:
            system_message = "You are a helpful assistant designed to output a Docker Compose YAML configuration."
            user_message = f"Generate a Docker Compose v3 YAML configuration for services with the following Docker images: {', '.join(docker_images)}. Ensure that ports are properly configured for each service. The configuration should be compatible with docker-compose-plugin. Assume files on disk will be saved in /home/{ssh_user}/."

            response = openai.ChatCompletion.create(
                model="gpt-4-0613",
                messages=[
                    {"role": "system", "content": system_message},
                    {"role": "user", "content": user_message}
                ],
                temperature=0.7,
                max_tokens=1500,
                n=1,
                stop=None
            )

            # Extract the YAML content from the assistant's response
            docker_compose_yaml = response['choices'][0]['message']['content']

            # Write the YAML content to a file
            create_file("docker-compose.yml", docker_compose_yaml)  # Updated path
            return docker_compose_yaml

        except Exception as e:
            print(f"Error generating Docker Compose YAML: {e}")
            import traceback
            traceback.print_exc()
            return None
    else:
        print("Error: Neither Docker images nor a Compose file path was provided.")
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
                ingress_entries.append(f"echo \"    - hostname: {app_hostname}\\n      service: http://localhost:{container_port}\" >> /etc/cloudflared/config.yml")

    # Generate the cloudflare script using the ingress entries
    cloudflare_script = f"""#!/bin/bash
# Add cloudflare gpg key
sudo mkdir -p --mode=0755 /usr/share/keyrings
curl -fsSL https://pkg.cloudflare.com/cloudflare-main.gpg | sudo tee /usr/share/keyrings/cloudflare-main.gpg >/dev/null

# Add this repo to your apt repositories
echo 'deb [signed-by=/usr/share/keyrings/cloudflare-main.gpg] https://pkg.cloudflare.com/cloudflared jammy main' | sudo tee /etc/apt/sources.list.d/cloudflared.list

# install cloudflared
sudo apt-get update && sudo apt-get install -y cloudflared
sudo cloudflared tunnel login
sudo cloudflared tunnel create {formatted_hostname}
sudo cloudflared tunnel route ip add {static_ip}/32 {formatted_hostname}
tunnel_id=$(sudo cloudflared tunnel info {formatted_hostname} | grep -oP 'id:\\s*\\K[\\w-]+')

# Create config file
sudo mkdir -p /etc/cloudflared
echo "tunnel: {formatted_hostname}" | sudo tee /etc/cloudflared/config.yml
echo "credentials-file: /root/.cloudflared/$tunnel_id.json" | sudo tee -a /etc/cloudflared/config.yml
echo "protocol: quic" | sudo tee -a /etc/cloudflared/config.yml
echo "logfile: /var/log/cloudflared.log" | sudo tee -a /etc/cloudflared/config.yml
echo "loglevel: debug" | sudo tee -a /etc/cloudflared/config.yml
echo "transport-loglevel: info" | sudo tee -a /etc/cloudflared/config.yml
echo "ingress:" | sudo tee -a /etc/cloudflared/config.yml
"""

    # Add ingress entries
    for entry in ingress_entries:
        cloudflare_script += f"{entry}\n"

    # Add the default 404 service and additional commands
    cloudflare_script += """echo "    - service: http_status:404" | sudo tee -a /etc/cloudflared/config.yml
sudo cloudflared service install
sudo systemctl start cloudflared
sudo systemctl status cloudflared
"""

    # Write the complete script to a file
    create_file("setup_cloudflare.sh", cloudflare_script)

# Create a file with specified content in the app directory
def create_file(file_name, content):
    file_path = os.path.join(app_dir, file_name)  # Create the full path
    with open(file_path, "w") as file:
        file.write(content)

# Update the review_and_deploy function to reference the new paths
def review_and_deploy():
    print("\nSetup completed. The following files have been generated:")
    generated_files = [
        "setup.tf",
        "setup_server.sh",
        "setup_cloudflare.sh",
        "docker-compose.yml",
        "docker-compose.service",
        "updater.sh"
    ]

    # Check if a Dockerfile was added
    if dockerfile_path:
        generated_files.append("Dockerfile")

    for file in generated_files:
        file_path = os.path.join(app_dir, file)  # Update to use the new path
        if os.path.exists(file_path):
            print(f"- {file}: {file_path}")

    if not compose_file_path and docker_images:
        print("\nWARNING: The Docker Compose file was generated by OpenAI. Please review it carefully before deployment.")

    print("\nPlease review these files carefully before proceeding.")

    while True:
        choice = input("\nChoose an option:\n1. Exit script (to review files manually)\n2. Proceed with deployment\nEnter your choice (1 or 2): ")

        if choice == "1":
            print("Exiting script. To deploy later, run the following commands manually:")
            print(f"cd {app_dir}")
            print("terraform init")
            print("terraform apply")
            return
        elif choice == "2":
            print("Proceeding with deployment...")
            try:
                os.chdir(app_dir)  # Change to the app directory
                subprocess.run(["terraform", "init"], check=True)
                result = subprocess.run(["terraform", "apply", "-auto-approve"], capture_output=True, text=True, check=True)
                print("Deployment completed successfully.")

                # Extract the IP address from Terraform output
                output_lines = result.stdout.split('\n')
                ip_address = next((line.split('=')[1].strip() for line in output_lines if 'instance_ip' in line), None)

                if ip_address:
                    print(f"\nYour instance IP address is: {ip_address}")
                    print("\nNext steps:")
                    print(f"1. SSH into your new server:")
                    print(f"   ssh -i {ssh_private_key_path} {ssh_user}@{ip_address}")
                    print("2. Run the server setup script:")
                    print("   sudo sh /opt/setup_server.sh")
                    print("3. Configure Cloudflare Tunnel:")
                    print("   sudo sh /opt/setup_cloudflare.sh")
                    print("\nFollow the prompts in each script to complete the setup.")
                else:
                    print("Unable to retrieve the instance IP address. Please check the Terraform output manually.")
            except subprocess.CalledProcessError as e:
                print(f"An error occurred during deployment: {e}")
            return
        else:
            print("Invalid choice. Please enter 1 or 2.")

# Main script execution
project_id = fetch_project_id()
static_ip, formatted_hostname = check_static_ip(app_hostname, region)
ssh_private_key_path = vars.get("ssh_private_key_path")

if static_ip is None or formatted_hostname is None:
    print("Error: Unable to obtain static IP or formatted hostname.")
    exit(1)

# Extract SSH user and public key from the public key file
ssh_user = get_ssh_user_from_key(ssh_public_key_path)
ssh_public_key = read_ssh_public_key(ssh_public_key_path)

if ssh_user is None or ssh_public_key is None:
    print("Error: Unable to extract SSH user or public key from the public key file.")
    exit(1)

# Fetch the service account key and get the filename only
credentials_path = fetch_service_account_key()
credentials_filename = os.path.basename(credentials_path)  # Get just the filename

# Generate setup_server.sh
docker_pull_commands = "\n".join([f"docker pull {image}" for image in docker_images])

# Determine whether to include Docker pull commands based on conditions
if compose_file_path or dockerfile_path:
    docker_pull_commands = ""  # Do not include Docker pull commands

create_file("setup_server.sh", f"""#!/bin/bash 
# Update and Install Dependencies
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg lsb-release

# Add Docker's official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --batch --yes --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# Add the repository to Apt sources
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

# Update apt repositories
sudo apt-get update

# Install Docker
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# Start and enable Docker service
sudo systemctl start docker
sudo systemctl enable docker

# Pull Docker images
{docker_pull_commands}

# Change to the working directory
cd /opt

# Rebuild Docker images without cache
sudo docker compose build --no-cache

# Start Docker Compose
sudo docker compose up -d

# Enable Docker Compose service
sudo systemctl enable docker-compose.service
""")

# Generate docker-compose.service
create_file("docker-compose.service", """[Unit]
Description=Docker Compose Application Service
Requires=docker.service
After=docker.service

[Service]
Type=simple
WorkingDirectory=/opt
ExecStart=/usr/bin/docker compose -f /opt/docker-compose.yml up
ExecStop=/usr/bin/docker compose -f /opt/docker-compose.yml down
Restart=always
RestartSec=5s

[Install]
WantedBy=multi-user.target
""")

# Generate updater.sh
docker_pull_commands = "\n".join([f"docker pull {image}" for image in docker_images])
create_file("updater.sh", f"""#!/bin/bash
# Update the package index
sudo apt update

# Upgrade Docker and Cloudflared
sudo apt upgrade -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin cloudflared

# Pull latest docker images
{docker_pull_commands}

# Stop current setup
sudo docker compose stop

# Delete docker-containers (data is stored separately)
sudo docker compose rm -f

# Start Docker again
sudo docker compose -f /opt/docker-compose.yml up -d
""")

# Generate Docker Compose YAML
docker_compose_yaml = generate_docker_compose_yaml(OPENAI_API_KEY, docker_images, ssh_user, compose_file_path)

if docker_compose_yaml:
    # Generate Cloudflare Script updating ports based on YAML
    generate_cloudflare_script(docker_compose_yaml, formatted_hostname, static_ip, app_hostname)
else:
    print("Error: Failed to generate or copy Docker Compose YAML.")
    exit(1)

# Generate Terraform configuration
generate_terraform_config(project_id, static_ip, credentials_path, ssh_user, ssh_public_key, vars.get("os_type"), vars.get("server_type"), dockerfile_path, compose_file_path)

# Call the review_and_deploy function to allow the user to review files before deployment
review_and_deploy()
