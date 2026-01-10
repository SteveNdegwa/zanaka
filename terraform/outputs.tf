output "vps_host" {
  description = "The IP address or hostname of the VPS"
  value       = var.vps_host
}

output "docker_image_tag" {
  description = "Docker image tag deployed on the server"
  value       = var.docker_image_tag
}

output "app_url" {
  description = "The URL for the Django app"
  value       = "http://api.${var.base_domain}"
}

output "portainer_url" {
  description = "URL for Portainer dashboard"
  value       = "http://portainer.${var.base_domain}"
}

output "grafana_url" {
  description = "URL for Grafana dashboard"
  value       = "http://grafana.${var.base_domain}"
}

output "flower_url" {
  description = "URL for Celery Flower monitoring"
  value       = "http://flower.${var.base_domain}"
}
