import pynetbox
import logging
import ipaddress
from dotenv import load_dotenv
import os

# load variables from .env file 
load_dotenv()

# Prepare loggging 
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# import variables for .env file
netbox_url = os.getenv("NETBOX_URL")
api_token = os.getenv("API_TOKEN")
tenant_name = os.getenv("TENANT_NAME")
tenant_group_name = os.getenv("TENANT_GROUP_NAME")
vlan_id = int(os.getenv("VLAN_ID"))
vlan_name = os.getenv("VLAN_NAME")
ip_start_address = os.getenv("IP_START_ADDRESS")
ip_end_address = os.getenv("IP_END_ADDRESS")
prefix = os.getenv("PREFIX")
site_name = os.getenv("SITE_NAME")
tag_name = os.getenv("TAG_NAME")
prefix_status = os.getenv("PREFIX_STATUS", "active")  # status 

# connect to Netbox Api
logging.info("Connecting to NetBox API...")
nb = pynetbox.api(netbox_url, token=api_token)

# check and create Tag
logging.info(f"Checking for tag '{tag_name}'...")
tag = nb.extras.tags.get(name=tag_name)
if tag:
    logging.info(f"Tag '{tag_name}' already exists.")
else:
    logging.info(f"Tag '{tag_name}' not found, creating it.")
    tag = nb.extras.tags.create(name=tag_name, slug=tag_name.lower())

# check and create Tenant Group 
logging.info(f"Checking for tenant group '{tenant_group_name}'...")
group_arazcloud = nb.tenancy.tenant_groups.get(name=tenant_group_name)
if group_arazcloud:
    logging.info(f"Tenant group '{tenant_group_name}' already exists.")
else:
    logging.info(f"Tenant group '{tenant_group_name}' not found, creating it.")
    group_arazcloud = nb.tenancy.tenant_groups.create(name=tenant_group_name)

# check and create Tenant
logging.info(f"Checking for tenant '{tenant_name}'...")
tenant_arazcloud = nb.tenancy.tenants.get(name=tenant_name)
if tenant_arazcloud:
    logging.info(f"Tenant '{tenant_name}' already exists.")
else:
    logging.info(f"Tenant '{tenant_name}' not found, creating it.")
    tenant_arazcloud = nb.tenancy.tenants.create(name=tenant_name)

# Check and create Site 
logging.info(f"Checking for site '{site_name}'...")
site = nb.dcim.sites.get(name=site_name)
if site:
    logging.info(f"Site '{site_name}' already exists.")
else:
    logging.info(f"Site '{site_name}' not found, creating it.")
    site = nb.dcim.sites.create(name=site_name, slug=site_name.lower())

# Check and create Vlan 
logging.info(f"Checking for VLAN '{vlan_name}'...")
existing_vlan = nb.ipam.vlans.get(vid=vlan_id)
if existing_vlan:
    logging.info(f"VLAN '{vlan_name}' already exists with ID {existing_vlan.id}.")
    vlan_id = existing_vlan.id  # Use existence Vlan ID
else:
    logging.info(f"VLAN '{vlan_name}' not found, creating it.")
    vlan_data = {
        "vid": vlan_id,  # Vlan ID
        "name": vlan_name,  # Vlan name 
        "tenant": tenant_arazcloud.id if tenant_arazcloud else None,  # Tenant
        "tags": [tag.id],  # Tag
        "status": "active"  # Vlan status
    }
    vlan = nb.ipam.vlans.create(vlan_data)
    if vlan:
        logging.info(f"VLAN {vlan.name} created successfully with ID {vlan.vid}.")
        vlan_id = vlan.id  # New Prefix for Vlan ID
    else:
        logging.error("Error creating VLAN.")
        vlan_id = None  # Get None value if it dosent create 

# Check and create Prefix
if vlan_id:
    logging.info(f"Checking for prefix '{prefix}'...")
    existing_prefix = nb.ipam.prefixes.get(prefix=prefix)
    if existing_prefix:
        logging.info(f"Prefix '{prefix}' already exists.")
    else:
        logging.info(f"Prefix '{prefix}' not found, creating it.")
        prefix_data = {
            "prefix": prefix,
            "status": prefix_status,
            "tenant": tenant_arazcloud.id if tenant_arazcloud else None,
            "site": site.id if site else None,
            "tags": [tag.id],
            "vlan": vlan_id  # Used find or created Vlan ID
        }
        created_prefix = nb.ipam.prefixes.create(prefix_data)
        if created_prefix:
            logging.info(f"Prefix {prefix} created successfully.")
        else:
            logging.error("Error creating prefix.")
else:
    logging.error("Cannot create prefix because VLAN ID is invalid or missing.")

# Enter all ips in IP range 
logging.info(f"Adding individual IP addresses from {ip_start_address} to {ip_end_address}...")
network_range = ipaddress.summarize_address_range(ipaddress.IPv4Address(ip_start_address), ipaddress.IPv4Address(ip_end_address))

for network in network_range:
    for ip in network.hosts():
        ip_str = str(ip) + "/32"
        existing_ip = nb.ipam.ip_addresses.get(address=ip_str)
        if existing_ip:
            logging.info(f"IP address {ip_str} already exists.")
        else:
            logging.info(f"Adding IP address {ip_str}...")
            try:
                new_ip = nb.ipam.ip_addresses.create(
                    address=ip_str,
                    tenant=tenant_arazcloud.id if tenant_arazcloud else None,
                    tags=[tag.id],
                    status="active",
                    vlan=vlan_id  # Attach to Vlan 
                )
                logging.info(f"IP address {ip_str} added successfully.")
            except Exception as e:
                logging.error(f"Error adding IP address {ip_str}: {e}")

