variable "mounts" {
  description = "List of volumes to be mounted in the instance. One list item is a list itself with values [ fs_spec, fs_file, fs_vfstype, fs_mntops, fs-freq, fs_passno ]"
  default     = []
  type        = list(list(string))
}
