variable "gemini_api_key" {
  description = "Gemini API key from Google AI Studio"
  type        = string
  sensitive   = true
}

variable "slack_webhook_url" {
  description = "Slack incoming webhook URL"
  type        = string
  sensitive   = true
}
