# GrabBite — Deployment Guide

Full deployment documentation for running GrabBite in production.

---

## Option 1 — Traditional VPS (Ubuntu/Debian)

**1. Server setup**

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv nginx -y

git clone <repository-url>
cd Grabbite

python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

**2. Configure environment**

```bash
cp .env.example .env
nano .env
```

Minimum production values:

```env
SECRET_KEY=<generate-a-64-byte-random-key>
FLASK_ENV=production
FLASK_DEBUG=0
DATABASE_URL=postgresql://user:password@localhost/grabbite
MAIL_SERVER=smtp.gmail.com
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password
RAZORPAY_KEY_ID=your-key-id
RAZORPAY_KEY_SECRET=your-key-secret
ADMIN_EMAIL=admin@yourdomain.com
ADMIN_PASSWORD=<strong-password>
```

**3. Configure Nginx**

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /path/to/Grabbite/static;
    }

    location /socket.io {
        proxy_pass http://127.0.0.1:5000/socket.io;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/grabbite /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl restart nginx
```

**4. Systemd service**

```ini
# /etc/systemd/system/grabbite.service
[Unit]
Description=GrabBite Flask Application
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/Grabbite
Environment="PATH=/path/to/Grabbite/.venv/bin"
ExecStart=/path/to/Grabbite/.venv/bin/python run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now grabbite
```

**5. SSL with Let's Encrypt**

```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

---

## Option 2 — Docker

```bash
# Build and start (app + PostgreSQL)
docker-compose up -d --build

# View logs
docker-compose logs -f web
```

The included `Dockerfile` and `docker-compose.yml` are ready to use. Set your secrets via environment variables or a `.env` file before starting.

---

## Option 3 — Cloud Platforms

| Platform    | Steps                                                                               |
| ----------- | ----------------------------------------------------------------------------------- |
| **Heroku**  | Add a `Procfile` with `web: python run.py`, attach Heroku Postgres, set config vars |
| **Railway** | Connect the GitHub repo, set env vars in the dashboard, auto-deploys on push        |
| **Render**  | Same as Railway — connect repo, set env vars, deploy                                |

---

## Monitoring & Logs

```bash
# App logs
sudo journalctl -u grabbite -f

# Nginx access log
sudo tail -f /var/log/nginx/access.log
```

Set up [Sentry](https://sentry.io) for production error tracking.

---

## Production Checklist

- [ ] `SECRET_KEY` set to a random 64-byte value
- [ ] `FLASK_ENV=production`, `FLASK_DEBUG=0`
- [ ] `DATABASE_URL` pointing to PostgreSQL
- [ ] `ADMIN_EMAIL` and `ADMIN_PASSWORD` set
- [ ] HTTPS / SSL certificate configured
- [ ] SMTP credentials configured for emails
- [ ] Razorpay **live** keys set (not test keys)
