output "instance_id"  { value = module.ec2.instance_id }
output "public_ip"    { value = module.ec2.public_ip }
output "ssh_command"  { value = module.ec2.ssh_command }
output "bootstrap_log" { value = module.ec2.bootstrap_log }
