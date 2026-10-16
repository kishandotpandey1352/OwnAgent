variable "aws_region" {
  description = "AWS region."
  type        = string
  default     = "us-east-1"
}

variable "cluster_version" {
  description = "EKS Kubernetes version."
  type        = string
  default     = "1.31"
}

variable "vpc_cidr" {
  description = "CIDR block for the EKS VPC."
  type        = string
  default     = "10.40.0.0/16"
}

variable "cpu_node_instance_types" {
  description = "Instance types for CPU node group."
  type        = list(string)
  default     = ["m6i.large", "m7i.large"]
}

variable "gpu_node_instance_types" {
  description = "Instance types for GPU node group."
  type        = list(string)
  default     = ["g5.xlarge"]
}

variable "cpu_node_desired_size" {
  type    = number
  default = 2
}

variable "cpu_node_min_size" {
  type    = number
  default = 1
}

variable "cpu_node_max_size" {
  type    = number
  default = 3
}

variable "gpu_node_desired_size" {
  type    = number
  default = 0
}

variable "gpu_node_min_size" {
  type    = number
  default = 0
}

variable "gpu_node_max_size" {
  type    = number
  default = 1
}

variable "hf_token_secret_value" {
  description = "Optional Hugging Face token value. Prefer setting this later manually or through secure CI/CD."
  type        = string
  default     = ""
  sensitive   = true
}

variable "api_key_secret_value" {
  description = "API key value for inference API."
  type        = string
  default     = "dev-finance-api-key"
  sensitive   = true
}
