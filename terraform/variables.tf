variable "region" {
  description = "AWS region"
  type        = string
  default     = "us-east-1"
}

variable "project" {
  description = "Project name for tagging"
  type        = string
  default     = "NimbusKart"
}

variable "environment" {
  description = "Environment name for tagging"
  type        = string
  default     = "staging"
}

variable "owner" {
  description = "Owner name for tagging"
  type        = string
  default     = "devops-team"
}

variable "ssh_cidr" {
  description = "CIDR block allowed for SSH access — restrict this in production"
  type        = string
  default     = "0.0.0.0/0"
}

variable "stopped_instance_days" {
  description = "Number of days an instance can be stopped before flagged as orphan"
  type        = number
  default     = 14
}