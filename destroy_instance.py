import subprocess
import json
import os

# Load global variables from a file
def load_variables():
    variables = {}
    with open("variables.txt", "r") as file:
        for line in file:
            if "=" in line:
                key, value = line.split("=", 1)
                variables[key.strip()] = value.strip().strip('"')
    return variables

# Check if variables.txt exists
if not os.path.exists("variables.txt"):
    print("variables.txt file is required to run this script.")
    exit(1)

# Load variables from variables.txt
vars = load_variables()

# Get variables
app_hostname = vars.get("app_hostname")
region = vars.get("region")
formatted_hostname = app_hostname.replace('.', '-')  # Format hostname for GCP

# Function to confirm deletion
def confirm_deletion():
    print(f"Instance to be deleted: {formatted_hostname}")
    print(f"Static IP to be deleted: {formatted_hostname}")  # Assuming the static IP has the same name
    print("The following firewall rules will also be deleted: http-ingress, https-ingress")
    confirmation = input("Are you sure you want to delete the above resources? (yes/no): ")
    return confirmation.lower() == 'yes'

# Function to delete firewall rules
def delete_firewall_rules():
    rules = ["http-ingress", "https-ingress"]
    for rule in rules:
        result = subprocess.run(
            ["gcloud", "compute", "firewall-rules", "delete", rule, "--quiet"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            print(f"Error deleting firewall rule {rule}:", result.stderr)
        else:
            print(f"Firewall rule {rule} deleted successfully.")

# Function to delete the GCP instance
def delete_instance():
    print(f"Deleting instance: {formatted_hostname}")
    result = subprocess.run(
        ["gcloud", "compute", "instances", "delete", formatted_hostname, "--zone", f"{region}-a", "--quiet"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Error deleting instance:", result.stderr)
    else:
        print("Instance deleted successfully.")

# Function to delete the static IP
def delete_static_ip():
    print(f"Deleting static IP: {formatted_hostname}")
    result = subprocess.run(
        ["gcloud", "compute", "addresses", "delete", formatted_hostname, "--region", region, "--quiet"],
        capture_output=True, text=True
    )
    if result.returncode != 0:
        print("Error deleting static IP:", result.stderr)
    else:
        print("Static IP deleted successfully.")

# Main execution
if confirm_deletion():
    delete_firewall_rules()
    delete_instance()
    delete_static_ip()
else:
    print("Deletion canceled.")