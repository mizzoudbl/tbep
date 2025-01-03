# Target & Biomarker Exploration Portal

## Table of Contents

- [About](#about)
- [Server Configuration](#server-configuration)
- [Installation](#installation)
- [License](#license)
- [Troubleshooting & FAQs](#troubleshooting--faqs)

## About

We present a novel web-based bio-informatics tool designed to facilitate the identification of novel therapeutic targets and biomarkers for drug discovery. The tool integrates multi-omics datasets rooted in human genetics and utilizes experimentally validated protein-protein interaction (PPI) networks to perform genome-wide analyses of proteins that physically interact with genes responsible for disease phenotypes. A key feature of this tool is its real-time large-scale data processing capability, enabled by its efficient architecture and cloud-based framework. Additionally, the tool incorporates an integrated large language model (LLM) to assist scientists in exploring biological insights from the generated network and multi-omics data. The LLM enhances the interpretation and exploration of complex biological relationships, offering a more interactive and intuitive analysis experience. This integration of multi-omics data, PPI networks, and AI-driven exploration provides a powerful framework for accelerating the discovery of novel drug targets and biomarkers.

## Server Configuration

1. Install essential packages & open firewall ports:

    ```bash
    # Install essential packages
    sudo apt update -y
    sudo apt install -y git nginx
    sudo systemctl enable nginx
    sudo systemctl start nginx

    # Open firewall ports
    sudo ufw enable
    sudo ufw allow 'Nginx Full' 'Nginx Full(v6)' 'OpenSSH' 'OpenSSH (v6)'
    ```

2. Install docker:

    ```bash
    # Add Docker's official GPG key:
    sudo apt-get update
    sudo apt-get install ca-certificates curl
    sudo install -m 0755 -d /etc/apt/keyrings
    sudo curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
    sudo chmod a+r /etc/apt/keyrings/docker.asc

    # Add Docker APT repository:
    echo "deb [signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

    # Install Docker
    sudo apt-get update
    sudo apt-get install docker-ce docker-ce-cli containerd.io

    # Add user to docker group
    sudo groupadd docker
    sudo usermod -aG docker $USER
    newgrp docker
    ```

3. Configure nginx:

    ```bash
    # Create a new server block (change filename as per requirement)
    sudo vim /etc/nginx/conf.d/<domain-name>.conf
    # Frontend configuration
    ```

    ```bash
    server {
        listen 80;
        # Can change the hosting link accordingly
        server_name <domain-name>;

        location / {
            # Change the port as per requirement
            proxy_pass http://localhost:5000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }
    ```

    ```bash
    # Backend configuration (change filename as per your requirement)
    sudo vim /etc/nginx/conf.d/<domain-name>.conf
    ```

    ```bash
    server {
        listen 80;
        # Can change the hosting link accordingly
        server_name <domain-name>;

        location / {
            # Change the port as per requirement
            proxy_pass http://localhost:3000;
            proxy_http_version 1.1;
            proxy_set_header Upgrade $http_upgrade;
            proxy_set_header Connection 'upgrade';
            proxy_set_header Host $host;
            proxy_cache_bypass $http_upgrade;
        }
    }
    ```

    ```bash
    # Test nginx configuration
    sudo nginx -t

    # Reload nginx
    sudo systemctl reload nginx
    ```

4. Now, follow the [Installation](#installation) steps to setup the project. After the process, configure SSL encryption (for https) using certbot if required.

    ```bash
    # Install certbot
    sudo apt-get update
    sudo apt-get install certbot python3-certbot-nginx

    # Obtain SSL certificate 
    # Make sure to change the domain name as per requirement
    sudo certbot --nginx -d <domain-name>
    ```

## Installation

1. Clone the repository

    ```bash
    git clone --depth 1 --recurse-submodules https://github.com/bhupesh98/tbep.git && cd tbep
    ```

2. Fill environment variables in `.env`, `backend/.env` & `frontend/.env` using [`.env.example`](.env.example), [`backend/.env.example`](https://github.com/bhupesh98/tbep-backend/blob/main/.env.example) & [`frontend/.env.example](https://github.com/bhupesh98/tbep-frontend/blob/main/.env.example) file.

    ```bash
    cp .env.example .env
    cp backend/.env.example backend/.env
    cp frontend/.env.example frontend/.env
    ```

3. Download the video files from the following link and place them inside the `frontend/public/video/` folder.

    **NOTE:** This is not the most conventional & intuitive place to keep the videos, but this was hard-coded in the frontend code, so directed to keep the videos in this folder. This will soon be changed and once done will be updated in the manual. Also, this workflow will be gradually improved to avoid these steps, but currently the video size exceeds 100MB limit of commit size, so this is the workaround.

4. Docker compose up the database and seed the data. Keep the database dump inside the [scripts](scripts) folder.

    > 💡 **NOTE**
    > In case, the server doesn't have the dump data. Transfer the files using the following command:
    >
    > ```bash
    > # Transfer files to the server
    > scp -r <source-path> <username>@<server-ip>:<destination-path>
    > ```

    ```bash
    docker compose up -d --build
    docker exec -it neo4j neo4j-admin database load --from-path=/var/lib/neo4j/import/ tbep
    # Change the username (default username is neo4j) and password
    docker exec -it neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "CREATE DATABASE tbep; START DATABASE tbep;"
    ```

    > NOTE: To dump the database for data migration. Use this command:
    >
    > ```bash
    > # First, stop the database
    > docker compose exec -it neo4j cypher-shell -u neo4j -p $NEO4J_PASSWORD "STOP DATABASE tbep;"
    > # Dump the database
    > docker exec -it neo4j neo4j-admin database dump tbep --to-path=/var/lib/neo4j/import/backups
    > ```

5. Once, data is seeded successfully and database is online. Restart the neo4j service.

```bash
docker compose restart neo4j
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Troubleshooting & FAQs

1. File permissions error in frontend container running leading to unable to view pages on website. This may occur when working on restrictive company servers.
**Fix:**

    ```bash
    docker exec -it frontend chmod -R 777 /usr/share/nginx/html
    ```

2. Latest changes missing in the frontend.
**Fix:**
Pull latest changes relevant branch.

```bash
git pull
# OR
# git pull origin <branch-name>
```
