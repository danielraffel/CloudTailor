#!/bin/bash

# Checks if a given command exists in the system's PATH.
# Usage: command_exists <command>
command_exists() {
    type "$1" &> /dev/null
}

# Loads and checks variables from the variables.txt file.
# Exits the script if any required variables are unset.
load_variables() {
    if [ -f "variables.txt" ]; then
        echo "Loading variables from variables.txt..."
        source "variables.txt"

        # Check for unset required variables
        if [ -z "$app_hostname" ] || [ -z "$docker_images" ] || [ -z "$region" ] \
           || [ -z "$os_type" ] || [ -z "$server_type" ] || [ -z "$ssh_public_key_path" ] \
           || [ -z "$OPENAI_API_KEY" ]; then
            echo "One or more variables are unset in variables.txt. Please fill them out and run the script again (or delete variables.txt.)"
            exit 1
        fi
        return 0
    else
        echo "variables.txt not found."
        return 1
    fi
}

# Function to prompt user input for a variable, with an option to use a default value.
ask_and_set() {
    local var_name=$1
    local message=$2
    local default_value=$3
    local confirmation
    local input

    while true; do
        echo "$message"
        read -p "Enter value ($default_value): " input
        input=${input:-$default_value}
        echo "You entered: $input"
        read -p "Is this correct? (y/n): " confirmation
        if [[ $confirmation == "y" ]]; then
            eval "$var_name='$input'"
            break
        fi
    done
}

# Function to prompt for Google Cloud region
prompt_for_region() {
    local confirmed="n"
    while [[ $confirmed != "y" ]]; do
        echo "\nPlease select the Google Cloud region for your VM:"
        echo " 1) Oregon: us-west1"
        echo " 2) Iowa: us-central1"
        echo " 3) South Carolina: us-east1"
        read -p "Select a region (1/2/3): " region_choice

        case "$region_choice" in
            1) REGION="us-west1" ;;
            2) REGION="us-central1" ;;
            3) REGION="us-east1" ;;
            *) echo "Invalid choice. Please select a valid option."; continue ;;
        esac

        read -p "You selected: $REGION. Is this correct? (y/n): " confirmed
    done
}

# Function to prompt for GCP server type
prompt_for_server_type() {
    local server_choice
    local server_confirmed="n"
    while [[ $server_confirmed != "y" ]]; do
        echo "\nSelect the type of GCP server:"
        echo " 1) e2-micro (FREE)"
        echo " 2) e2-small"
        echo " 3) e2-medium"
        echo " 4) custom (enter a custom server type)"
        read -p "Select an option (1/2/3/4): " server_choice

        case "$server_choice" in
            1) SERVER_TYPE="e2-micro" ;;
            2) SERVER_TYPE="e2-small" ;;
            3) SERVER_TYPE="e2-medium" ;;
            4) read -p "Enter custom server type: " SERVER_TYPE ;;
            *) echo "Invalid choice. Please select a valid option."; continue ;;
        esac

        read -p "You selected: $SERVER_TYPE. Is this correct? (y/n): " server_confirmed
    done
}

# Function to prompt for OS selection
prompt_for_os() {
    local os_choice
    local os_confirmed="n"
    while [[ $os_confirmed != "y" ]]; do
        echo "\nSelect the OS for your server:"
        echo " 1) ubuntu-os-cloud/ubuntu-2204-lts"
        echo " 2) ubuntu-os-cloud/ubuntu-2004-lts"
        echo " 3) cos-cloud/cos-arm64-109-lts"
        echo " 4) centos-cloud/centos-stream-9"
        echo " 5) other (enter Image project/Image family)"
        read -p "Select an option (1/2/3/4/5): " os_choice

        case "$os_choice" in
            1) OS_TYPE="ubuntu-os-cloud/ubuntu-2204-lts" ;;
            2) OS_TYPE="ubuntu-2004-lts" ;;
            3) OS_TYPE="cos-cloud/cos-arm64-109-lts" ;;
            4) OS_TYPE="centos-cloud/centos-stream-9" ;;
            5) read -p "Enter other OS image name Image project/Image family: " OS_TYPE ;;
            *) echo "Invalid choice. Please select a valid option."; continue ;;
        esac

        read -p "You selected: $OS_TYPE. Is this correct? (y/n): " os_confirmed
    done
}

# Prompts the user to continue with the script execution.
echo "This script automates the deployment of a Google Cloud VM with the Docker images of your choice.\nA Python script generates a Terraform file and other scripts.\nOpenAI is used to generate the Docker YAML file based on the software you choose to install."
read -p "Do you want to proceed? (y/n): " proceed
if [[ $proceed != "y" ]]; then
    echo "Exiting script."
    exit 0
fi

# Checks for the presence of necessary CLI tools.
if ! command_exists gcloud || ! command_exists terraform || ! command_exists python3; then
    echo "Please ensure Google CLI, Terraform, Python3, and required PIP packages are installed."
    exit 1
fi

# Attempt to load variables from the variables.txt file
if ! load_variables; then
    echo "Setting up configuration..."

    # Set app_hostname variable
    ask_and_set app_hostname "Enter your domain (e.g., YOUR.DOMAIN.COM):" "YOUR.DOMAIN.COM"

    # Prompt for Google Cloud region
    prompt_for_region

    # Prompt for GCP server type
    prompt_for_server_type

    # Prompt for OS selection
    prompt_for_os

    # Set SSH key paths
    ask_and_set ssh_public_key_path "Please enter the path to your SSH public key:" "for example: ~/.ssh/gcp.pub"

    # Docker images configuration
    ask_and_set docker_images "Enter Docker images to install (separate multiple with a space: teslamate/teslamate:latest n8nio/n8n):" ""

    # OpenAI API key configuration
    ask_and_set OPENAI_API_KEY "Please enter your OpenAI API key:" ""

    # Generate variables.txt file
    echo "Creating variables.txt with the configuration..."
    echo "app_hostname=\"$app_hostname\"" > variables.txt
    echo "docker_images=\"$docker_images\"" >> variables.txt
    echo "region=\"$REGION\"" >> variables.txt
    echo "os_type=\"$OS_TYPE\"" >> variables.txt
    echo "server_type=\"$SERVER_TYPE\"" >> variables.txt
    echo "ssh_public_key_path=\"$ssh_public_key_path\"" >> variables.txt
    echo "OPENAI_API_KEY=\"$OPENAI_API_KEY\"" >> variables.txt
fi

# Run the Python script
echo "Running the Python script with your selected options..."
python3 setup.py
