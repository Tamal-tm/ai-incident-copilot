resource "aws_apigatewayv2_api" "copilot_api" {
  name          = "ai-incident-copilot-api"
  protocol_type = "HTTP"
}

resource "aws_apigatewayv2_integration" "lambda_integration" {
  api_id                 = aws_apigatewayv2_api.copilot_api.id
  integration_type       = "AWS_PROXY"
  integration_uri        = aws_lambda_function.copilot.invoke_arn
  payload_format_version = "2.0"
}

resource "aws_apigatewayv2_route" "alert_route" {
  api_id    = aws_apigatewayv2_api.copilot_api.id
  route_key = "POST /alert"
  target    = "integrations/${aws_apigatewayv2_integration.lambda_integration.id}"
}

resource "aws_apigatewayv2_stage" "default" {
  api_id      = aws_apigatewayv2_api.copilot_api.id
  name        = "$default"
  auto_deploy = true
}

resource "aws_lambda_permission" "apigw_invoke" {
  statement_id  = "apigateway-invoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.copilot.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_apigatewayv2_api.copilot_api.execution_arn}/*/*"
}
