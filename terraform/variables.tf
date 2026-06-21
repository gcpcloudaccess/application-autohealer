variable "project_id" {
  description = "GCP project ID"
  type        = string
}

variable "region" {
  description = "GCP region for the GKE cluster"
  type        = string
  default     = "us-central1"
}

variable "zone" {
  description = "GCP zone for the GKE cluster"
  type        = string
  default     = "us-central1-a"
}

variable "cluster_name" {
  description = "Name of the GKE cluster"
  type        = string
  default     = "autopilot-standard-cluster"
}

variable "network" {
  description = "VPC network for the GKE cluster"
  type        = string
  default     = "default"
}

variable "subnetwork" {
  description = "Subnetwork for the GKE cluster (optional)"
  type        = string
  default     = ""
}

variable "node_pool_name" {
  description = "Name for the primary node pool"
  type        = string
  default     = "primary-node-pool"
}

variable "node_count" {
  description = "Initial number of nodes in the node pool"
  type        = number
  default     = 3
}

variable "min_node_count" {
  description = "Minimum number of nodes for autoscaling"
  type        = number
  default     = 1
}

variable "max_node_count" {
  description = "Maximum number of nodes for autoscaling"
  type        = number
  default     = 3
}

variable "machine_type" {
  description = "Machine type for the GKE nodes"
  type        = string
  default     = "e2-medium"
}
