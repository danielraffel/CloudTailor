# CloudTailor: Streamlining Docker Deployment on GCP with Cloudflare, Terraform, and OpenAI

[Blog post](https://danielraffel.me/2024/01/12/cloudtailor/) with high-level project walkthrough

## Overview

CloudTailor aims to simplify the setup of a Google Cloud Platform (GCP) VM, tailored for users new to GCP or those seeking an easier way to deploy Docker containers. By combining bash and Python scripts, it streamlines VM setup, Docker image deployment using Terraform, and establishes a secure Cloudflare Tunnel.

Key features include:
- Automated setup of GCP VMs with customized configurations
- Flexible Docker deployment options:
  1. AI-generated Docker Compose files based on specified images
  2. User-provided Docker Compose files
  3. Combination of specified images and user-provided Compose files
- Integration with OpenAI for intelligent configuration suggestions
- Cloudflare Tunnel setup for secure SSL access
- Terraform-based infrastructure management with optional automated deployment

Ideal for hobbyists or individuals with basic technical knowledge interested in exploring various software applications on GCP's free-tier E2 micro-instances.

## Purpose of This Utility

This tool automates and simplifies the process of configuring servers for software experimentation or deployment on the Google Cloud platform. It's designed to eliminate redundancy in server setup and make it more efficient to quickly set up and experiment with software.

### Use Cases

- **For Developers Experimenting with Google Cloud and Docker:** Deploy Docker containers on Google Cloud quickly without needing GCP knowledge. Ideal for those testing out applications in isolated environments.
  
- **For Hobbyists Running Personal Projects:** Run your favorite software stacks, like home automation or personal websites, on GCP’s free-tier VMs without worrying about manually setting up the infrastructure.

- **For Small Teams or Startups:** Simplify the setup of cloud servers with secure access via Cloudflare Tunnel. Quickly deploy Docker Compose applications in a repeatable, automated way, making it easier to focus on app development.

- **For Individuals Exploring AI:** Use OpenAI to suggest Docker Compose configurations based on your application needs, removing the complexity of manually writing config files.  

## Prerequisites

Install and configure the following before running the `config.sh` bash script:

1. **Terraform**: [Installation Guide](https://www.terraform.io/downloads.html)
2. **Google Cloud SDK**: [Installation Guide](https://cloud.google.com/sdk/docs/install)
3. **Google CLI Authorization**: Run `gcloud auth login`
4. **[Enable Google Cloud Engine](https://console.cloud.google.com/compute/)**
5. **Python 3**: Confirm with `python3 --version`
6. **PIP Packages**: `pip install subprocess YAML JSON os OpenAI`
7. **SSH Key**: [GitHub Guide](https://docs.github.com/en/authentication/connecting-to-github-with-ssh/generating-a-new-ssh-key-and-adding-it-to-the-ssh-agent)
8. **Domain Hosted with [Cloudflare](https://cloudflare.com) DNS**
9. **[OpenAI API Key](https://platform.openai.com/api-keys)**

## What the Scripts Do

### Bash Script (`config.sh`)
- Performs initial checks and configurations
- Guides the user through the setup process
- Offers Docker configuration options:
  1. Specify Docker images for AI-generated Compose file
  2. Provide a path to an existing Docker Compose or Dockerfile
  3. Generate Terraform files to deploy
- Provides an option at the end of the script:
  1. **Exit Script** to manually review and deploy the Terraform files
  2. **Proceed with Deployment** where the script automatically deploys the Terraform configuration to GCP
- If you select the automated deployment option, it will handle the entire Terraform deployment process based on your configuration and guide you through the necessary SSH steps for post-deployment server setup and Cloudflare Tunnel configuration.

### Python Script (`setup.py`)
- Reads configuration from `variables.txt`
- Manages GCP resources (project ID, service account, static IP)
- Uses existing Docker Compose or Dockerfile, or generates a new Compose file using OpenAI based on provided images
- Copies `service-account-key.json` from the parent directory if available to avoid re-downloading

### Terraform file (`setup.tf`)
- Provisions a GCP instance with specified configurations
- Sets up network interfaces and firewall rules
- Uploads necessary files to the server

### Destroy Instance and Config Script (`destroy_instance.py`)
- To make it easy to "start over fresh" this script will delete:
  1. GCP VM
  2. Associated Static IP
  3. Firewall rules (http-ingress, https-ingress).
- Run the following command to delete the instance. It will display what can be deleted and prompt you for confirmation before proceeding:
   ```bash
   python destroy_instance.py
   ```

## Usage

### Step 1: Initial Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/danielraffel/CloudTailor.git
   cd CloudTailor
   ```

2. Run the configuration script:
   ```bash
   sh config.sh
   ```
   Follow the prompts to set up your desired GCP environment and choose your Docker images / configuration options.

  **At the end of the script, you will be presented with two options:** 
   - **Option 1**: Exit the script and manually review and deploy the Terraform files. Proceed to Step 2. 
   - **Option 2**: Proceed with the automated Terraform deployment, which will handle the deployment to GCP based on your configuration. Proceed to Step 3.

   Note: Either option requires you to complete Step 3 for post-deployment configuration.

### Step 2 (Optional): Manual Terraform Deployment

1. Review generated files before proceeding.
2. Initialize Terraform:
   ```bash
   terraform init
   ```

3. Apply the Terraform configuration:
   ```bash
   terraform apply
   ```

4. When prompted, type 'yes' to confirm the deployment.

### Step 3: Post-Deployment Configuration

Regardless of whether you chose manual or automated deployment, SSH into your new server and run the scripts:

1. SSH into your new server using the IP address provided by the script or Terraform output:
   ```bash
   ssh -i ~/.ssh/your_private_key_file username@your_instance_ip
   ```

2. Run the server setup script:
   ```bash
   sudo sh /opt/setup_server.sh
   ```

3. Configure Cloudflare Tunnel:
   ```bash
   sudo sh /opt/setup_cloudflare.sh
   ```
   The script will guide you through this process, including Cloudflare authentication and tunnel creation.

### Step 4: Verify Deployment

To verify:
1. Check that your Docker containers are running:
   ```bash
   sudo docker ps
   ```

2. Verify that Cloudflare Tunnel is active:
   ```bash
   sudo systemctl status cloudflared
   ```

3. Access your application via the configured Cloudflare domain.

## Post-Deployment

- Your server will have Docker and Cloudflare Tunnel configured.
- Docker containers will be set up based on your chosen configuration method.

## Updating Server Software

SSH into your server and run:
```bash
sudo sh /opt/updater.sh
```

## Debugging

To debug Terraform issues, navigate to the directory named after your Virtual Machine in `CloudTailor` containing `setup.tf` and run:
```bash
terraform apply -auto-approve -input=false -no-color | tee terraform.log
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
```
