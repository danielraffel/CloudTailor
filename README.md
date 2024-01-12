# CloudTailor: Streamlining Docker Deployment on GCP with Cloudflare, Terraform and OpenAI

[Blog post](https://danielraffel.me/2024/01/12/cloudtailor/) with high-level project walkthrough

## Overview

This project aims to streamline the setup of a Google Cloud Platform (GCP) VM, specifically tailored for users new to GCP or seeking an easier way to deploy Docker containers so they can try out software. By combining bash and Python scripts, it simplifies the complexities of VM setup, Docker image deployment using Terraform, and establishing a secure Cloudflare Tunnel. Ideal for someone less familiar with GCP, Docker and Terraform, this tool aids in configuring and deploying servers with customized Docker images. It incorporates OpenAI's API for  configuration suggestions based on your software choices, enabling integration of SSL through Cloudflare on your Cloudflare hosted domain.

## Purpose of This Utility
This tool was developed to eliminate redundancy the author encountered in configuring servers for software experimentation or deployment. It aims to automate and simplify these processes, making it more efficient and accessible to quickly set up and experiment with software on the Google Cloud platform.

Note: **This is primarily designed for educational or experimental purposes and is not intended for production environments.** While it is generally effective in generating functional code, it is relying _a bit_ on AI generated software configurations and may not always succeed. _It is particularly suited for hobbyists or individuals with basic technical knowledge who are interested in setting up a free-tier E2 micro-instance virtual machines on GCP to explore or test various software applications._

## Prerequisites
Install and configure before running the `config.sh` bash script
1. **Terraform**: Install Terraform for infrastructure management. [Installation Guide](https://www.terraform.io/downloads.html)
2. **Google Cloud SDK**: Essential for interacting with GCP. [Installation Guide](https://cloud.google.com/sdk/docs/install)
3. **Google CLI Authorization**: Ensure you've authenticated the Google CLI with your account. You will need to have previously authorized your account by running: `gcloud auth login`
4. **[Enable Google Cloud Engine](https://console.cloud.google.com/compute/)**: For the CLI to work autonomously you will need to have previously enabled GCP's Cloud Engine.
5. **Python 3**: Required for running the Python script. Confirm its installation in a terminal with `python3 --version`.
6. **PIP Packages**: Install the required Python packages: `pip install subprocess YAML JSON os OpenAI`
7. **SSH Key**: Generate an SSH key and note the name you give it. [GitHub Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
8. **Domain Hosted with [Cloudflare](https://cloudflare.com) DNS**: Required for [Cloudflare tunnel](https://www.cloudflare.com/products/tunnel/) configuration.
9. **[OpenAI API Key](https://platform.openai.com/api-keys)**: Required for OpenAI integration to generate the Docker YAML file.

## What the Scripts Do

### Bash Script (`config.sh`)
The `config.sh` script is responsible for preparing the environment for running the `setup.py` Python script. It performs initial checks, configurations, and user interactions. Here's an overview of its functionality:

- **Initial Setup and User Interaction:**
  - Introduces the purpose of the script to the user and prompts for confirmation to proceed.
  - Checks for the presence of necessary CLI tools (Google CLI, Terraform, Python3) and advises on required installations if any are missing.

- **Variables File Loading and Validation:**
  - Attempts to load global variables from `variables.txt`. If the file doesn't exist or if any required variables are missing, the script prompts the user to input these details.
  - Validates that all necessary variables are set, including `app_hostname`, `docker_images`, `region`, `os_type`, `server_type`, `ssh_public_key_path`, and `OPENAI_API_KEY`.

- **Interactive Configuration Setup:**
  - If `variables.txt` is incomplete or missing, the script guides the user through setting up various configuration parameters:
    - Domain name (`app_hostname`).
    - SSH public key path.
    - Docker images to be installed.
    - OpenAI API key.
    - Google Cloud region.
    - Server type (e.g., e2-micro, e2-small).
    - Operating system for the server.
  - Each input is validated for correctness before proceeding.

- **Script Execution with `variables.txt` :**
  - If `variables.txt` already exists and has validated then `setup.py` will run using its configurations.
  - if `variables.txt` does not exist the bash script will create it with the users configurations and then `setup.py` will run using its configurations.
 
### Python Script (`setup.py`)
This script automates the setup of a server environment, including Docker containers, Cloudflare tunnel configuration, and a Google Cloud Platform (GCP) instance. Here's what the script does:

- **Read Global Variables:** Imports configuration details from `variables.txt`, ensuring customizability of the script for different environments and needs.

- **GCP Project and Service Account Key:** Fetches the GCP project ID and service account key to interact with GCP resources.

- **Static IP Address Management:** Checks for an existing static IP address in GCP or creates a new one. This IP is used for the server instance, ensuring a consistent point of access.

- **Terraform Configuration Generation (`setup.tf`):** Generates a Terraform configuration file to establish a GCP instance with specified properties like OS type, server type, and SSH configurations.

- **Docker Compose YAML Generation:** Uses OpenAI's GPT model to generate a `docker-compose.yml` file based on specified Docker images. This file orchestrates the deployment of Docker containers.

- **Script and Configuration File Generation:**
  - `setup_server.sh` – Installs and configures Docker and its dependencies on the server.
  - `setup_cloudflare.sh` – Configures Cloudflare tunnel for secure, external access to the server.
  - `updater.sh` – A utility script to update Docker images and restart containers.
  - `docker-compose.yml` – Generated by the script, this file defines the Docker multi-container setup.
  - `docker-compose.service` – A systemd service unit file to manage the lifecycle of the Docker Compose application.

- **Cloudflare Tunnel Configuration:**
  - The script dynamically creates the Cloudflare `config.yml` based on the ports defined in the `docker-compose.yml`.
  - Parses each service in the Docker Compose YAML to extract port mappings.
  - For each port, it adds an ingress entry in the Cloudflare configuration, ensuring that the correct ports are exposed through the Cloudflare tunnel.

- **Execution Flow:**
  - The script executes sequentially, ensuring each step is completed before proceeding to the next.
  - Error checking is included to handle potential issues during the setup process.
 
### Terraform file (`setup.tf`)
The Terraform configuration (setup.tf) provisions the following on GCP:
- A new GCP instance consisting of a VM with the machine type and OS of your choice with a 60gb boot disk, and standard static IP network interface.
- Uploads files to the server: /opt/setup_server.sh, /opt/setup_cloudflare.sh, /opt/updater.sh, /opt/docker-compose.yml, and /etc/systemd/system/docker-compose.service

## Usage

### Step 1: Initial Setup

- Clone the repository and navigate to it.
   ```
  git clone https://github.com/danielraffel/CloudTailor.git
  cd CloudTailor
  ```

- Run the bash script to configure global variables and prepare the environment.
  ```
  sh setup.sh
  ```

### Step 2: Deploy with Terraform
Strongly advise reviewing the files the python script generates before running `terraform apply` to ensure there are no configuration details that appear to require further customization (before being uploaded to your server.)

- Initialize Terraform:
  ```
  terraform init
  ```
- Apply the Terraform configuration:
  ```
  terraform apply
  ```
- Confirm deployment when prompted.

### Step 3: Server Configuration

- SSH into the server using the provided IP and your SSH key.
  ```
  ssh -i ~/.ssh/gcp USERNAME@X.X.X.X
  ```

- Run the `setup_server.sh` script to configure Docker and other services.
  ```
  sudo sh /opt/setup_server.sh
  ```


- Run the `setup_cloudflare.sh` script to configure CloudFlare Tunnel so you are using SSL.
  ```
  sudo sh /opt/setup_cloudflare.sh
  ```
  Follow the instructions to set up the Cloudflare tunnel. When prompted, copy/paste the URL in a browser and then select the domain you want to tunnel and authorize it. The cert will be downloaded to the server and your DNS name will be updated with the tunnelID.
  
## Post-Deployment

- The server will have Docker and Cloudflare Tunnel configured.
- Docker images specified will be pulled and set up.
- Cloudflare tunnel provides secure SSL access to your domain.


## Updating Server Software

- SSH into your server in a terminal:
  ```
  ssh -i ~/.ssh/gcp USERNAME@X.X.X.X
  ```
- Run the updater script on the server (to upgrade Docker, n8n, FastAPI and Cloudflare Tunnel):
  ```
  sudo sh /opt/updater.sh
  ```

## Cost Considerations

- Depends on the machine type of your choice. The E2 micro-instance falls under GCP's always-free tier, but always check the latest policies of Google, Cloudflare Tunnel, and any Docker images used.

## How to Delete What This Script Creates

### On Google Cloud

- **VM**: Delete the created VM through the GCP console.
- **Static IP**: Release the static IP if not in use to avoid charges.

### On Cloudflare

- **Tunnel**: Delete the created tunnel via Cloudflare Dashboard.
- **Subdomain**: Remove the configured subdomain in your DNS settings.

## Best Compatibility with Ubuntu VMs
Presently, this utility is optimized for setting up Ubuntu servers, as the generated scripts specifically utilize Ubuntu's package installer (`apt-get`). While it's possible to select non-Ubuntu operating systems, be aware that you'll need to manually adjust the installer scripts this generates to align with the package management system of your chosen OS. Assuming you know what you're doing you should be able to easily modify the generated scripts _either_ locally before running the Terraform commands _or afterwards_ on your new VM once Terraform has uploaded them.

## (Potential) Future Enhancements
- Extend script support to include operating systems beyond macOS.
- Implement a logic check in the script to verify the compatibility of selected OS and Machine Type combinations, including diverse processor architectures.
- Integrate Docker Hub queries to validate the availability and compatibility of Docker images.
- Introduce a feature to save and retrieve commonly used configuration combinations.
- Strengthen the prerequisites verification process to ensure all necessary tools and dependencies are present. (currently doesn't check python packages)
- Enable bash script to offer to
   -  install any missing necessary tools and dependencies if not present.
   - generate ssh key if non existent.
   - activate gcloud services via the CLI which may not automatically configure. (this may be working automatically)
- Expand script compatibility to accommodate various VM operating systems (currently Ubuntu focused.)
- Modify the Terraform configuration to adapt the package management commands in setup_server.sh, setup_cloudflare.sh, and updater.sh based on the chosen OS. For instance:
   - If `ubuntu-os-cloud` is chosen, use `apt-get` for package management. (currently the default support)
   - If `cos-cloud` is selected, switch to `apk`. *not supported*
   - For `centos-cloud`, employ `yum`. *not supported*
- Enhance the ReadMe documentation to provide more comprehensive details about the utility, including its expanded features and capabilities.
