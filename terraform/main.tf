resource "null_resource" "zanaka_server" {
  connection {
    type        = "ssh"
    host        = var.vps_host
    user        = var.ssh_user
    private_key = var.ssh_private_key
  }

  # Step 0: Ensure /opt/zanaka exists and is owned by the ssh user
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 0: Ensure /opt/zanaka exists and set ownership'",
      "sudo mkdir -p /opt/zanaka",
      "sudo chown ${var.ssh_user}:${var.ssh_user} /opt/zanaka"
    ]
  }

  # Step 1: Copy the docker-compose.yml from local repo to server
  provisioner "file" {
    source      = "${path.module}/../docker-compose.yml"
    destination = "/opt/zanaka/docker-compose.yml"
  }

  # Step 2: System update & essentials
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 1: Update system and install essentials'",
      "sudo apt-get update -y",
      "sudo apt-get install -y docker.io git curl nginx software-properties-common",
      "sudo systemctl enable docker",
      "sudo systemctl start docker",
      "sudo systemctl enable nginx",
      "sudo systemctl start nginx"
    ]
  }

  # Step 3: Install Docker Compose v2
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 2: Install Docker Compose v2'",
      "DOCKER_COMPOSE_VERSION=2.21.0",
      "if ! command -v docker-compose >/dev/null || [ $(docker-compose version --short) != $DOCKER_COMPOSE_VERSION ]; then",
      "  sudo curl -L https://github.com/docker/compose/releases/download/$DOCKER_COMPOSE_VERSION/docker-compose-$(uname -s)-$(uname -m) -o /usr/local/bin/docker-compose",
      "  sudo chmod +x /usr/local/bin/docker-compose",
      "fi"
    ]
  }

  # Step 4: Create project directories
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 3: Create project directories'",
      "mkdir -p /opt/zanaka/static",
      "cd /opt/zanaka"
    ]
  }

  # Step 5: Generate .env from Terraform variables
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 4: Generate .env file'",
      <<-EOT
      cat > /opt/zanaka/.env <<EOF
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
    ]
  }

  # Step 6: Copy docker-compose.yml
  provisioner "file" {
    source      = "${path.module}/../docker-compose.yml"
    destination = "/opt/zanaka/docker-compose.yml"
  }

  # Step 7: Start Docker stack
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 6: Pull and start Docker stack'",
      "cd /opt/zanaka",
      "sudo docker-compose pull",
      "sudo docker-compose up -d",
      "sudo docker-compose exec -T zanaka python manage.py collectstatic --noinput"
    ]
  }

  # Step 8: Nginx configuration
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 7: Configure Nginx'",
      <<-EOT
      sudo bash -c 'cat > /etc/nginx/sites-available/zanaka.conf <<EOF
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
      EOF'
      EOT
    ]
  }

  # Step 9: Enable site & reload Nginx
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 8: Enable Nginx site and reload'",
      "sudo ln -s /etc/nginx/sites-available/zanaka.conf /etc/nginx/sites-enabled/ || true",
      "sudo nginx -t",
      "sudo systemctl reload nginx"
    ]
  }

  # Step 10: Install Certbot and SSL
  provisioner "remote-exec" {
    inline = [
      "set -x",
      "echo 'Step 9: Install Certbot and configure SSL'",
      "sudo apt-get install -y certbot python3-certbot-nginx",
      "sudo certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d api.${var.base_domain} || true",
      "sudo certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d portainer.${var.base_domain} || true",
      "sudo certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d grafana.${var.base_domain} || true",
      "sudo certbot --nginx --non-interactive --agree-tos -m stevencallistus19@gmail.com -d flower.${var.base_domain} || true",
      "sudo systemctl reload nginx"
    ]
  }
}
