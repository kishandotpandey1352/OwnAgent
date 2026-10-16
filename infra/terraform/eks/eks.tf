module "eks" {
  source  = "terraform-aws-modules/eks/aws"
  version = "~> 20.0"

  cluster_name    = local.cluster_name
  cluster_version = var.cluster_version

  vpc_id     = module.vpc.vpc_id
  subnet_ids = module.vpc.private_subnets

  enable_irsa = true

  enable_cluster_creator_admin_permissions = true

  cluster_endpoint_public_access  = true
  cluster_endpoint_private_access = true

  cluster_addons = {
    coredns                = {}
    kube-proxy             = {}
    vpc-cni                = {}
    eks-pod-identity-agent = {}
  }

  eks_managed_node_groups = {
    cpu = {
      name = "finllm-dev-cpu"

      iam_role_name            = "finllm-dev-cpu-ng-role"
      iam_role_use_name_prefix = false

      instance_types = var.cpu_node_instance_types

      min_size     = var.cpu_node_min_size
      max_size     = var.cpu_node_max_size
      desired_size = var.cpu_node_desired_size

      capacity_type = "ON_DEMAND"

      labels = {
        workload = "system"
      }
    }

    gpu = {
      name = "finllm-dev-gpu"

      iam_role_name            = "finllm-dev-gpu-ng-role"
      iam_role_use_name_prefix = false

      instance_types = var.gpu_node_instance_types

      block_device_mappings = {
        xvda = {
          device_name = "/dev/xvda"

          ebs = {
            volume_size           = 100
            volume_type           = "gp3"
            encrypted             = true
            delete_on_termination = true
          }
        }
      }

      min_size     = var.gpu_node_min_size
      max_size     = var.gpu_node_max_size
      desired_size = var.gpu_node_desired_size

      capacity_type = "ON_DEMAND"

      ami_type = "AL2023_x86_64_NVIDIA"

      labels = {
        workload    = "gpu"
        accelerator = "nvidia"
      }

      taints = {
        gpu = {
          key    = "nvidia.com/gpu"
          value  = "true"
          effect = "NO_SCHEDULE"
        }
      }
    }
  }

  tags = local.common_tags
}
