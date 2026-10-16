data "aws_caller_identity" "current" {}

data "aws_availability_zones" "available" {
  state = "available"
}

locals {
  project_name = "finance-llm-platform"
  environment  = "dev"

  name_prefix  = "${local.project_name}-${local.environment}"
  cluster_name = "${local.name_prefix}-eks"

  account_id = data.aws_caller_identity.current.account_id
  region     = var.aws_region

  azs = slice(data.aws_availability_zones.available.names, 0, 3)

  common_tags = {
    Project     = local.project_name
    Environment = local.environment
    ManagedBy   = "terraform"
    Repo        = "finetuning-finance"
  }
}
