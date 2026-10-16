resource "aws_ecr_repository" "training" {
  name                 = "${local.name_prefix}-training"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "inference" {
  name                 = "${local.name_prefix}-inference"
  image_tag_mutability = "MUTABLE"

  image_scanning_configuration {
    scan_on_push = true
  }
}
