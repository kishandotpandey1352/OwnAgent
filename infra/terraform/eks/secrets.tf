resource "aws_secretsmanager_secret" "hf_token" {
  name        = "${local.name_prefix}/hf-token"
  description = "Optional Hugging Face token for model download."
}

resource "aws_secretsmanager_secret_version" "hf_token" {
  count = var.hf_token_secret_value == "" ? 0 : 1

  secret_id     = aws_secretsmanager_secret.hf_token.id
  secret_string = var.hf_token_secret_value
}

resource "aws_secretsmanager_secret" "api_key" {
  name        = "${local.name_prefix}/api-key"
  description = "API key for finance inference API."
}

resource "aws_secretsmanager_secret_version" "api_key" {
  secret_id     = aws_secretsmanager_secret.api_key.id
  secret_string = var.api_key_secret_value
}
