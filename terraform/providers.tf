terraform {
  required_version = ">= 1.5.6"

  required_providers {
    null = {
      source  = "hashicorp/null"
      version = "3.2.1"
    }
  }
}

provider "null" {}
