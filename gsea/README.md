# GSEA Installation

## Configuring nginx

```bash
# Create a new server block (change filename as per requirement)
sudo vim /etc/nginx/conf.d/pdnet-rnd-papis.conf
# Frontend configuration
```

```bash
server {
    listen 80;
    # Can change the hosting link accordingly
    server_name pdnet-rnd-papis.crecientech.com;

    location / {
        # Change the port as per requirement
        proxy_pass http://localhost:8000;
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

> Note 📝: SSL Encryption have to be enabled for the subdomain. You may use certbot application, if you want to implement that and the company allows it. Procedure for the same is available in main README file.

## Starting the container

> Attention ℹ️: This command needs to be executed in the root directory of the project where the `docker-compose.yml` file is located.

```bash
# --build tag can be removed if the image is already built and not modified
docker compose up -d --build gsea
```
