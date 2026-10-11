# ==============================================================================
# Ansible Inventory Generator: Dynamic .tftpl Rendering (Rule 7.2 & 8.2)
# ==============================================================================
# Purpose:
#   Automatically provisions and renders the target host inventory for Ansible
#   using Terraform's native templatefile() engine and the local_file provider.
#   Ensures zero manual copy-pasting across terraform apply / destroy cycles.
# ==============================================================================

resource "local_file" "ansible_inventory" {
  filename = "${path.module}/../ansible/inventory.ini"
  content  = templatefile("${path.module}/templates/inventory.ini.tftpl", {
    instance_id = aws_instance.chatbot.id
    ssh_user    = "ubuntu"
  })
}
