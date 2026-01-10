resource "null_resource" "zanaka_server" {
  connection {
    type        = "ssh"
    host        = var.vps_host
    user        = var.ssh_user
    private_key = var.ssh_private_key
  }

  # Copy the docker-compose.yml from local repo to server
  provisioner "file" {
    source      = "${path.module}/../docker-compose.yml"
    destination = "/opt/zanaka/docker-compose.yml"
  }

  provisioner "remote-exec" {
    inline = [
      # --- System update & essentials ---
      "apt-get update -y",
      "apt-get install -y docker.io git curl nginx software-properties-common",
      "systemctl enable docker",
      "systemctl start docker",
      "systemctl enable nginx",
      "systemctl start nginx",

      # --- Install Docker Compose v2 ---
      <<-EOT
      DOCKER_COMPOSE_VERSION=2.21.0
      if ! command -v docker-compose >/dev/null || [ $(docker-compose version --short) != $DOCKER_COMPOSE_VERSION ]; then
        curl -L https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose
        chmod +x /usr/local/bin/docker-compose
      fi
      EOT
      ,

      # --- Create project directories ---
      "mkdir -p /opt/zanaka/static",
      "cd /opt/zanaka",

      # --- Generate .env from Terraform variables ---
      <<-EOT
      cat > .env <<EOF
      DJANGO_SECRET_KEY=${var.django_secret}
      DJANGO_DEBUG=True
      SQL_ENGINE=django.db.backends.postgresql
      SQL_USER=postgres
      SQL_PASSWORD=${var.db_password}
      SQL_DATABASE=notification_bus
      SQL_HOST=postgres
      SQL_PORT=5432
      RABBITMQ_USER=guest
      RABBITMQ_PASSWORD=${var.rabbitmq_password}
      RABBITMQ_HOST=rabbitmq
      RABBITMQ_PORT=5672
      RABBITMQ_VHOST=/
      DOCKER_IMAGE_TAG=${var.docker_image_tag}
      CELERY_BROKER_URL=amqp://guest:${var.rabbitmq_password}@rabbitmq:5672//
      EOF
      EOT
      ,

      # --- Start Docker stack ---
      "docker-compose pull",
      "docker-compose up -d",
      "docker-compose exec -T zanaka python manage.py collectstatic --noinput",

      # --- Nginx configuration ---
      <<-EOT
      cat > /etc/nginx/sites-available/zanaka.conf <<EOF
      # Django app
      server {
          listen 80;
          server_name api.${var.base_domain};

          location / {
              proxy_pass http://127.0.0.1:8000;
              proxy_set_header Host \$host;
              proxy_set_header X-Real-IP \$remote_addr;
              proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
          }

          location /static/ {
              alias /opt/zanaka/static/;
          }
      }

      # Portainer
      server {
          listen 80;
          server_name portainer.${var.base_domain};

          location / {
              proxy_pass http://127.0.0.1:9000;
              proxy_set_header Host \$host;
              proxy_set_header X-Real-IP \$remote_addr;
              proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
          }
      }

      # Grafana
      server {
          listen 80;
          server_name grafana.${var.base_domain};

          location / {
              proxy_pass http://127.0.0.1:3000;
              proxy_set_header Host \$host;
              proxy_set_header X-Real-IP \$remote_addr;
              proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
          }
      }

      # Flower
      server {
          listen 80;
          server_name flower.${var.base_domain};

          location / {
              proxy_pass http://127.0.0.1:5555;
              proxy_set_header Host \$host;
              proxy_set_header X-Real-IP \$remote_addr;
              proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
          }
      }
      EOF
      EOT
      ,

      # Enable site & reload Nginx
      "ln -s /etc/nginx/sites-available/zanaka.conf /etc/nginx/sites-enabled/ || true",
      "nginx -t",
      "systemctl reload nginx",

      # --- Install Certbot for SSL ---
      "apt-get install -y certbot python3-certbot-nginx",
      # Attempt SSL issuance; ignore failures if DNS not pointing yet
      "certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d api.${var.base_domain} || true",
      "certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d portainer.${var.base_domain} || true",
      "certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d grafana.${var.base_domain} || true",
      "certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d flower.${var.base_domain} || true",
      "systemctl reload nginx"
    ]
  }
}
