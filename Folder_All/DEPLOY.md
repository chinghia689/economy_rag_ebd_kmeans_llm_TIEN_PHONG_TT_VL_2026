# Deploy vietecochat.site

This project serves the React frontend with Nginx and proxies `/api` to the FastAPI backend on `127.0.0.1:8001`.

## DNS

Create DNS records:

```text
A      @      159.223.42.218
CNAME  www    vietecochat.site
```

Check DNS:

```bash
dig +short vietecochat.site
dig +short www.vietecochat.site
```

Both should resolve to `159.223.42.218`.

## First Deploy

```bash
sudo mkdir -p /var/www/chatbot-kinhte
sudo chown -R $USER:$USER /var/www/chatbot-kinhte
cd /var/www/chatbot-kinhte
git clone <YOUR_REPO_URL> .
cd Folder_All
cp .env.production.example .env
nano .env
```

Fill secrets in `.env`. On first backend start, known app settings are seeded into SQLite at `chatbot/data/login_sessions.db`. After that, SQLite is the runtime source of truth, so changing `.env` will not overwrite non-empty settings already in the DB.

Run backend:

```bash
docker-compose up -d --build
```

Build frontend:

```bash
cd /var/www/chatbot-kinhte/Folder_All/frontend_react
npm install
npm run build
```

Install Nginx site without touching existing sites:

```bash
sudo cp /var/www/chatbot-kinhte/Folder_All/deploy/nginx/vietecochat.site.conf /etc/nginx/sites-available/vietecochat.site
sudo ln -s /etc/nginx/sites-available/vietecochat.site /etc/nginx/sites-enabled/vietecochat.site
sudo nginx -t
sudo systemctl reload nginx
```

Enable HTTPS:

```bash
sudo certbot --nginx -d vietecochat.site -d www.vietecochat.site
```

## Update Deploy

```bash
cd /var/www/chatbot-kinhte
git pull
cd Folder_All
docker-compose up -d --build
cd frontend_react
npm install
npm run build
sudo nginx -t
sudo systemctl reload nginx
```

## Runtime Data

These paths must stay on the server and must not be committed:

```text
.env
chatbot/data/login_sessions.db
chroma_economy_db/
```

`login_sessions.db` contains API keys, users, payments, admin settings, and chat history.
