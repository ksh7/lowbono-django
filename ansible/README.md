# Dokku & Ansible Instructions

Ansible setup to automate the deployment and management of apps using Dokku on Ubuntu servers. It provides different roles for server setup, dokku application configuration, and app management across staging and production environments.

## Prerequisites

- Ansible installed on local machine
- Ubuntu server with SSH access
- SSH key pair for authentication
- Environment variables configuration in 1Password

## File Structure

```
ansible/
├── group_vars
│   └── all
│       └── main.yml
├── host_vars
│   └── ubuntu-server
│       └── main.yml
├── inventory
│   └── hosts
├── roles
│   ├── app_control
│   │   ├── tasks
│   │   │   └── main.yml
│   │   └── vars
│   │       └── main.yml
│   ├── app_scale
│   │   ├── tasks
│   │   │   └── main.yml
│   │   └── vars
│   │       └── main.yml
│   ├── app_status
│   │   ├── tasks
│   │   │   └── main.yml
│   │   └── vars
│   │       └── main.yml
│   ├── cloudflare_setup
│   │   ├── handlers
│   │   │   └── main.yml
│   │   └── tasks
│   │       ├── main.yml
│   │       └── setup_cloudflare.yml
│   ├── create_user
│   │   ├── handlers
│   │   │   └── main.yml
│   │   ├── tasks
│   │   │   ├── create_user.yml
│   │   │   └── main.yml
│   │   └── vars
│   │       └── main.yml
│   ├── dokku_app_setup
│   │   ├── tasks
│   │   │   ├── app_config.yml
│   │   │   ├── app_create.yml
│   │   │   ├── app_env_config.yml
│   │   │   ├── main.yml
│   │   │   ├── redis_create.yml
│   │   │   ├── redis_install.yml
│   │   │   └── redis_link.yml
│   │   └── vars
│   │       └── main.yml
│   ├── dokku_server_setup
│   │   ├── defaults
│   │   │   └── main.yml
│   │   ├── handlers
│   │   │   └── main.yml
│   │   └── tasks
|   |       ├── enable_ipv6.yml
│   │       ├── main.yml
│   │       └── setup_dokku.yml
│   ├── load_1password
│   │   ├── tasks
│   │   │   └── main.yml
│   │   └── vars
│   │       └── main.yml
│   └── security_setup
│       ├── files
│       │   └── reboot.sh
│       ├── handlers
│       │   └── main.yml
│       └── tasks
│           ├── essential_packages.yml
│           ├── fail2ban.yml
│           ├── main.yml
│           ├── ssh_security.yml
│           ├── system_updates.yml
│           └── ufw_firewall.yml
├── ansible.cfg
├── app_control.yml
├── app_scale.yml
├── app_status.yml
├── cloudflare_setup.yml
├── create_user.yml
├── dokku_app_setup.yml
├── dokku_server_setup.yml
├── security_setup.yml
├── site.yml
└── README.md
```

## Configuration


### Ensure 1Password Vaults Ready & User Is Logged In

1Password Documentation: https://developer.1password.com/docs/cli/get-started/

Setup proper Vaults, Items for environment variables

Login: `eval $(op signin)`

Get SSH Key: `op item get "<Item Name>" --field "private key" > /tmp/ssh_key`

### Host Vars Configuration

Configure host vars at `host_vars/ubuntu-server/main.yml`

To load from 1Password
```yaml
ansible_host: "{{ server_ip }}"
ansible_user: "{{ server_username }}"
...
```

To configure manually
```yaml
ansible_host: "ip-addr"
ansible_user: "username"
...
```

### 1Password Configuration

Configure 1Password vault, item names at `roles/load_1password/vars/main.yml`:

```yaml
# 1Password configuration
onepassword_vault: "vault-name"
onepassword_server_item: "server-configs-item-name"
...
```

`onepassword_server_item` is a master item that contains details like server ip, server username, staging app environment variables item name, staging app configurations variables item name, production app environment variables item name, production app configurations variables item name with each containing respective key-value pairs.

### Incremental Control of Tasks

All tasks are tagged incrementally. for eg: `dokku-app-scale` (runs all scale tasks), `dokku-app-scale-web-app` (only web app scale).

### App Type (Staging vs Production)
Use a CLI variable `app_type` with value `staging` or `production` to configure or control particular app.

For staging app: `ansible-playbook dokku_app_setup.yml -e "app_type=staging"`

For production app: `ansible-playbook dokku_app_setup.yml -e "app_type=production"`

### Playbook: Create User

```ansible-playbook create_user.yml -e "server_username=root"```

Note: You should set `ansible_user = "root"` in `host_vars/ubuntu-server/main.yml`

This will create new user. Name of new server user is loaded from 1Password at 'roles/create_user/vars/main.yml' in `new_server_username`


### Playbook: Security Setup

```ansible-playbook security_setup.yml```

This will update system, setup reboot schedule, install essential packages, setup UFW firewall, SSH security, Fail2Ban


### Playbook: Dokku Server Setup

```ansible-playbook dokku_server_setup.yml```

This will install Dokku, setup dokku ssh configuration, enable docker IPv6


### Playbook: Cloudflare Tunnel Setup

```ansible-playbook cloudflare_setup.yml```

This will install and setup cloudflared for tunnels

#### Tunnel Configuration
To install connector copy the configuration `sudo cloudflared service install <connector-key>` from Cloudflare Tunnel dashboard and install it on server. Once installed, you can connect to respective ports using tunnel dashboard.

Note: It needs to be installed only once for a server.

#### WWW to Root Redirect
Configure WWW to root redirect rule using `Redirect from WWW to root [Template]` available on Cloudflare.


### Playbook: Dokku App Setup

```ansible-playbook dokku_app_setup.yml -e 'app_type=staging'```

This will create a dokku app based on `app_type` (i.e. _staging_ or _production_) and set config, environment variables. Additionally, this will also install Redis plugin, create and setup redis app

Note: After this deploy your app onto server using `git remote add dokku dokku@server:<app-name>` and `git push dokku`

### Playbook:  App Scale

Scale Apps: ```ansible-playbook app_scale.yml -e 'app_type=staging'```

### Playbook: App Status

View App Status: ```ansible-playbook app_status.yml -e 'app_type=staging'```

### Playbook: App Control

TODO...