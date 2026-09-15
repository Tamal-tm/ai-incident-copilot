data "aws_ecr_repository" "copilot_repo" {
  name = "ai-incident-copilot"
}

data "aws_ecr_image" "copilot_image" {
  repository_name = "ai-incident-copilot"
  image_tag        = "latest"
}

resource "aws_lambda_function" "copilot" {
  function_name = "ai-incident-copilot"
  role          = aws_iam_role.lambda_role.arn
  package_type  = "Image"
  image_uri     = "${data.aws_ecr_repository.copilot_repo.repository_url}@${data.aws_ecr_image.copilot_image.image_digest}"
  timeout       = 90
  memory_size   = 512

  environment {
    variables = {
      GEMINI_API_KEY    = var.gemini_api_key
      SLACK_WEBHOOK_URL = var.slack_webhook_url
    }
  }
}
