# CloudTailor: Streamlining Docker Deployment on GCP with Cloudflare, Terraform and OpenAI

[Blog post](https://danielraffel.me/2024/01/12/cloudtailor/) with high-level project walkthrough

## Overview

CloudTailor aims to simplify the setup of a Google Cloud Platform (GCP) VM, tailored for users new to GCP or those seeking a slightly easier way to deploy Docker containers for their first time. By combining bash and Python scripts, it streamlines VM setup, Docker image deployment using Terraform, and establishes a secure Cloudflare Tunnel. I was motivated to learn how to use Terraform and this project helped me do that.

Key features include:
- Automated setup of GCP VMs with customized configurations
- Flexible Docker deployment options:
  1. AI-generated Docker Compose files based on specified images
  2. User-provided Docker Compose files
  3. Combination of specified images and user-provided Compose files
- Integration with OpenAI for intelligent configuration suggestions
- Cloudflare Tunnel setup for secure SSL access
- Terraform-based infrastructure management

Ideal for hobbyists or individuals with basic technical knowledge interested in exploring various software applications on GCP's free-tier E2 micro-instances.

## Purpose of This Utility

This tool automates and simplifies the process of configuring servers for software experimentation or deployment on the Google Cloud platform. It's designed to eliminate redundancy in server setup and make it more efficient to quickly set up and experiment with software.

**Note:** This tool is primarily for educational or experimental purposes and is not intended for production environments. While generally effective, it has a feature that relies partly on AI-generated software configurations and those may not always succeed.

## Prerequisites

Install and configure before running the `config.sh` bash script:

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
- Guides user through setup process
- Offers three Docker configuration options:
  1. Specify Docker images for AI-generated Compose file
  2. Provide path to existing local Docker Compose file
  3. Specify both Docker images and local Compose file path
- Creates or updates `variables.txt` with user inputs

### Python Script (`setup.py`)
- Reads configuration from `variables.txt`
- Manages GCP resources (project ID, service account, static IP)
- Generates Terraform configuration (`setup.tf`)
- Handles Docker Compose file:
  - Uses provided file if specified
  - Generates file using OpenAI if only images are specified
- Creates necessary scripts and configurations
- Configures Cloudflare Tunnel based on Docker Compose ports

### Terraform file (`setup.tf`)
- Provisions GCP instance with specified configurations
- Sets up network interfaces and firewall rules
- Uploads necessary files to the server

## Usage

### Step 1: Initial Setup

1. Clone the repository:
   ```
   git clone https://github.com/danielraffel/CloudTailor.git
   cd CloudTailor
   ```

2. Run the configuration script:
   ```
   sh config.sh
   ```
   Follow the prompts to set up your environment and choose your Docker configuration option.
   
   **Note:** At the end of this step, `config.sh` will provide an option to deploy with Terraform, but this is not required.

### Step 2: Deploy with Terraform

1. Review generated files before proceeding.

2. Initialize Terraform:
   ```
   terraform init
   ```

3. Apply the Terraform configuration:
   ```
   terraform apply
   ```

4. When prompted, type 'yes' to confirm the deployment.

5. Wait for Terraform to complete the deployment. This may take several minutes. You'll see a message indicating successful completion, along with output showing your instance's IP address. **Note:** At the end of this step, Terraform has deployed files to your new server and you will now need to proceed with the next steps to SSH into the server and run the installed scripts to complete the software setup and configure your Cloudflare configuration.

### Step 3: Post-Deployment Configuration

After Terraform completes, you need to manually run two scripts on your new server to finalize the setup:

1. SSH into your new server using the IP address provided in the Terraform output:
   ```
   ssh -i ~/.ssh/your_private_key_file username@your_instance_ip
   ```
   Replace `your_private_key_file` with the path to your SSH private key, `username` with your GCP username, and `your_instance_ip` with the IP address from the Terraform output.

2. Run the server setup script:
   ```
   sudo sh /opt/setup_server.sh
   ```
   This script will install Docker, pull your specified images, and set up the Docker Compose service.

3. Configure Cloudflare Tunnel:
   ```
   sudo sh /opt/setup_cloudflare.sh
   ```
   Follow the prompts to complete Cloudflare Tunnel setup. You'll need to authenticate with Cloudflare during this process.

### Step 4: Verify Deployment

After completing these steps, your server should be fully configured with Docker running your specified containers and Cloudflare Tunnel providing secure access.

To verify:
1. Check that your Docker containers are running:
   ```
   sudo docker ps
   ```

2. Verify that Cloudflare Tunnel is active:
   ```
   sudo systemctl status cloudflared
   ```

3. Try accessing your application through the domain you configured with Cloudflare.

If you encounter any issues, review the logs of the setup scripts and Docker containers for troubleshooting.

## Post-Deployment

- Your server will have Docker and Cloudflare Tunnel configured.
- Docker containers will be set up based on your chosen configuration method.
- Cloudflare Tunnel provides secure SSL access to your domain.

## Updating Server Software

SSH into your server and run:
```
sudo sh /opt/updater.sh
```

## Cost Considerations

Costs depend on the chosen machine type. E2 micro-instances are part of GCP's always-free tier, but always check the latest policies of Google, Cloudflare Tunnel, and any Docker images used.

## How to Delete Resources

### On Google Cloud
- Delete the VM through the GCP console.
- Release the static IP if not in use.

### On Cloudflare
- Delete the created tunnel via Cloudflare Dashboard.
- Remove the configured subdomain in your DNS settings.

## Best Compatibility

Currently optimized for Ubuntu servers. If selecting non-Ubuntu operating systems, manual adjustments to the generated scripts may be necessary.

## Potential Future Enhancements

- Extended OS support beyond macOS
- Improved OS and Machine Type compatibility checks
- Docker Hub integration for image validation
- Configuration saving and retrieval feature
- Enhanced prerequisites verification
- Automated installation of missing dependencies
- Expanded VM OS compatibility
- Dynamic package management adaptation in scripts
- Comprehensive documentation updates

## Contributing

Contributions to CloudTailor are welcome! Please feel free to submit pull requests, create issues or spread the word.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.