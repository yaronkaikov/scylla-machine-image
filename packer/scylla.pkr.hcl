variable "ssh_username" {}
variable "image_name" {}
variable "arch" {}
variable "product" {}
variable "repo" {}
variable "scylla_build_id" {}
variable "build_mode" {}
variable "scylla_version" {}
variable "scylla_build_sha_id" {}
variable "operating_system" {}
variable "build_tag" {}
variable "branch" {}
variable "scylla_full_version" {}
variable "scylla_machine_image_version" {}
variable "target" {}
variable "instance_type" {}
variable "source_os_filter" {}
variable "ami_regions" {
  type = string
  default = ""
}
variable "source_ami_owner" {
  type = string
  default = ""
}
variable "region" {
  type = string
  default = ""
}
variable "client_id" {
  type = string
  default = ""
}
variable "client_secret" {
  type = string
  default = ""
}
variable "tenant_id" {
  type = string
  default = ""
}
variable "subscription_id" {
  type = string
  default = ""
}
variable "image_offer" {
  type = string
  default = ""
}
variable "image_publisher" {
  type = string
  default = ""
}

source "azure-arm" "azure" {
  azure_tags = {
    arch                         = "${var.arch}"
    branch                       = "${var.branch}"
    build_id                     = "${var.scylla_build_id}"
    build_mode                   = "${var.build_mode}"
    build_tag                    = "${var.build_tag}"
    operating_system             = "${var.operating_system}"
    scylla_build_sha_id          = "${var.scylla_build_sha_id}"
    scylla_jmx_version           = "${var.scylla_full_version}"
    scylla_machine_image_version = "${var.scylla_machine_image_version}"
    scylla_python3_version       = "${var.scylla_full_version}"
    scylla_tools_version         = "${var.scylla_full_version}"
    scylla_version               = "${var.scylla_full_version}"
    user_data_format_version     = "3"
  }
  ssh_username = "${var.ssh_username}"
  client_id = "${var.client_id}"
  client_secret = "${var.client_secret}"
  tenant_id = "${var.tenant_id}"
  subscription_id = "${var.subscription_id}"
  managed_image_resource_group_name = "scylla-images"
  managed_image_name = regex_replace("${var.image_name}", ":", "-")
  os_type = "Linux"
  image_publisher = "${var.image_publisher}"
  image_offer = "${var.image_offer}"
  image_sku = "${var.source_os_filter}"
  vm_size = "${var.instance_type}"
  keep_os_disk = true
  private_virtual_network_with_public_ip = true
  build_resource_group_name = "scylla-images"
  virtual_network_name = "scylla-images"
}
source "amazon-ebs" "aws" {
  ami_block_device_mappings {
    device_name  = "/dev/sdb"
    virtual_name = "ephemeral0"
  }
  ami_block_device_mappings {
    device_name  = "/dev/sdc"
    virtual_name = "ephemeral1"
  }
  ami_block_device_mappings {
    device_name  = "/dev/sdd"
    virtual_name = "ephemeral2"
  }
  ami_block_device_mappings {
    device_name  = "/dev/sde"
    virtual_name = "ephemeral3"
  }
  ami_block_device_mappings {
    device_name  = "/dev/sdf"
    virtual_name = "ephemeral4"
  }
  ami_block_device_mappings {
    device_name  = "/dev/sdg"
    virtual_name = "ephemeral5"
  }
  ami_block_device_mappings {
    device_name  = "/dev/sdh"
    virtual_name = "ephemeral6"
  }
  ami_block_device_mappings {
    device_name  = "/dev/sdi"
    virtual_name = "ephemeral7"
  }
  aws_polling {
    delay_seconds = 30
    max_attempts  = 100
  }
  source_ami_filter {
    filters = {
       name = "${var.source_os_filter}"
    }
    owners = ["${var.source_ami_owner}"]
    most_recent = true
  }
  ami_name                    = regex_replace("${var.image_name}", ":", "-")
  ena_support   = true
  instance_type = "${var.instance_type}"
  launch_block_device_mappings {
    delete_on_termination = true
    device_name           = "/dev/sda1"
    volume_size           = 30
  }
  subnet_id = "subnet-ec4a72c4"
  security_group_id = "sg-c5e1f7a0"
  region = "${var.region}"
  ami_regions = [var.ami_regions]

  associate_public_ip_address = "true"
  shutdown_behavior         = "terminate"
  sriov_support             = true
  ssh_clear_authorized_keys = true
  ssh_timeout               = "5m"
  ssh_username              = "${var.ssh_username}"
  tags = {
    Name                         = "${var.image_name}"
    arch                         = "${var.arch}"
    branch                       = "${var.branch}"
    build_id                     = "${var.scylla_build_id}"
    build_mode                   = "${var.build_mode}"
    build_tag                    = "${var.build_tag}"
    operating_system             = "${var.operating_system}"
    scylla_build_sha_id          = "${var.scylla_build_sha_id}"
    scylla_jmx_version           = "${var.scylla_full_version}"
    scylla_machine_image_version = "${var.scylla_machine_image_version}"
    scylla_python3_version       = "${var.scylla_full_version}"
    scylla_tools_version         = "${var.scylla_full_version}"
    scylla_version               = "${var.scylla_full_version}"
    user_data_format_version     = "3"
  }
  user_data_file = "user_data.txt"
}
source "googlecompute" "gce" {
  disk_size         = 30
  image_description = "Official ScyllaDB image ${var.scylla_version}"
  image_family      = "scylla"
  project_id        = "scylla-images"
  image_labels = {
    arch                         = "${var.arch}"
    branch                       = "${var.branch}"
    build_id                     = "${var.scylla_build_id}"
    build_mode                   = "${var.build_mode}"
    build_tag                    = "${var.build_tag}"
    operating_system             = regex_replace("${var.operating_system}", "[. ~]", "-")
    scylla_build_sha_id          = "${var.scylla_build_sha_id}"
    scylla_jmx_version           = regex_replace("${var.scylla_full_version}", "[. ~]", "-")
    scylla_machine_image_version = regex_replace("${var.scylla_machine_image_version}", "[. ~]", "-")
    scylla_python3_version       = regex_replace("${var.scylla_full_version}", "[. ~]", "-")
    scylla_tools_version         = regex_replace("${var.scylla_full_version}", "[. ~]", "-")
    scylla_version               = regex_replace("${var.scylla_full_version}", "[. ~]", "-")
    user_data_format_version     = "3"
  }
  image_name              = "${lower(regex_replace("${var.image_name}", "[: . _]", "-"))}"
  labels = {
    keep        = 1
    keep_action = "terminate"
  }
  machine_type = "${var.instance_type}"
  metadata = {
    block-project-ssh-keys = "TRUE"
  }
  omit_external_ip    = false
  preemptible         = true
  source_image_family = "${var.source_os_filter}"
  ssh_timeout         = "6m"
  ssh_username        = "${var.ssh_username}"
  use_internal_ip     = false
  zone                = "${var.region}"
}
build {
  sources = [
    "source.azure-arm.azure",
    "source.amazon-ebs.aws",
    "source.googlecompute.gce"
  ]

  provisioner "file" {
    destination = "/home/${var.ssh_username}/"
    source      = "files/"
  }

  provisioner "file" {
    destination = "/home/${var.ssh_username}/"
    source      = "scylla_install_image"
  }

  provisioner "shell" {
    inline = ["sudo /usr/bin/cloud-init status --wait", "sudo /home/${var.ssh_username}/scylla_install_image --target-cloud ${var.target} --scylla-version ${var.scylla_full_version} --repo ${var.repo} --product ${var.product}"]
  }

  provisioner "file" {
    destination = "build/"
    direction   = "download"
    source      = "/home/${var.ssh_username}/${var.product}-packages-${var.scylla_full_version}-${var.arch}.txt"
  }

  provisioner "file" {
    destination = "build/"
    direction   = "download"
    source      = "/home/${var.ssh_username}/${var.product}-kernel-${var.scylla_full_version}-${var.arch}.txt"
  }

  provisioner "shell" {
    inline = ["if [ ${var.target} = gce -o ${var.target} = azure ]; then sudo userdel -r -f ${var.ssh_username}; fi"]
  }

  post-processor "manifest" {
    output = "manifest.json"
    strip_path = false
    custom_data = {
      image_name = regex_replace("${var.image_name}", ":", "-")
    }
  }
}
