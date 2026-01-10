variable "vps_host" {
  description = "IP address or hostname of the VPS"
}

variable "ssh_user" {
  description = "SSH user to connect to the VPS"
  default     = "root"
}

variable "ssh_private_key" {
  description = "Private SSH key for the VPS"
  sensitive   = true
}

variable "docker_image_tag" {
  description = "Tag of the Docker image to deploy"
}

variable "db_password" {
  description = "PostgreSQL password"
  sensitive   = true
}

variable "django_secret" {
  description = "Django SECRET_KEY"
  sensitive   = true
}

variable "rabbitmq_password" {
  description = "RabbitMQ password"
  sensitive   = true
}

variable "base_domain" {
  description = "Base domain for all subdomains"
  default     = "stmarysacademy.ac.ke"
}
