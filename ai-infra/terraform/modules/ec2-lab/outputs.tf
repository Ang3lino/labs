output "instance_id" {
  description = "EC2 instance ID."
  value       = aws_instance.lab.id
}

output "public_ip" {
  description = "Public IP address of the instance."
  value       = aws_instance.lab.public_ip
}

output "public_dns" {
  description = "Public DNS hostname of the instance."
  value       = aws_instance.lab.public_dns
}

output "ssh_command" {
  description = "Ready-to-use SSH command."
  value       = "ssh -i ~/.ssh/ai-infra ubuntu@${aws_instance.lab.public_ip}"
}

output "bootstrap_log" {
  description = "Command to tail the bootstrap log once SSH'd in."
  value       = "tail -f /var/log/bootstrap.log"
}
