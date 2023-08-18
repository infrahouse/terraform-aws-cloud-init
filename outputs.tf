output "userdata" {
  description = "Rendered user-data with cloudinit config."
  value       = data.template_cloudinit_config.config.rendered
}