output "userdata" {
  description = "Rendered user-data with cloudinit config."
  value       = data.cloudinit_config.config.rendered
  sensitive   = true
}
