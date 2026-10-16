output "cluster_name" {
  value = module.eks.cluster_name
}

output "cluster_endpoint" {
  value = module.eks.cluster_endpoint
}

output "vpc_id" {
  value = module.vpc.vpc_id
}

output "private_subnets" {
  value = module.vpc.private_subnets
}

output "artifacts_bucket" {
  value = aws_s3_bucket.artifacts.bucket
}

output "training_ecr_repository_url" {
  value = aws_ecr_repository.training.repository_url
}

output "inference_ecr_repository_url" {
  value = aws_ecr_repository.inference.repository_url
}
