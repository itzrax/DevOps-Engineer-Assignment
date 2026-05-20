output "vpc_id" {
  description = "The VPC ID"
  value       = module.network.vpc_id
}

output "subnet_ids" {
  description = "The public subnet IDs"
  value       = module.network.subnet_ids
}

output "bucket_name" {
  description = "The S3 app logs bucket name"
  value       = aws_s3_bucket.app_logs.bucket
}