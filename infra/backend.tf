terraform {
  required_version = ">= 1.5"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  backend "s3" {
    bucket         = "tamal-ai-incident-copilot-tfstate"
    key            = "terraform.tfstate"
    region         = "ap-south-1"
    dynamodb_table = "ai-incident-copilot-tf-lock"
    encrypt        = true
  }
}

provider "aws" {
  region = "ap-south-1"
}
