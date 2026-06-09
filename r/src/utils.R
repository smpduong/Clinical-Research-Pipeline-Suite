# ============================================================================
# utils.R - Shared Utility Functions (R Implementation)
# ============================================================================

# Null-coalescing operator
`%||%` <- function(x, y) if (is.null(x)) y else x

# Cohen's d effect size
cohens_d <- function(group1, group2) {
  n1 <- length(group1)
  n2 <- length(group2)
  pooled_sd <- sqrt(((n1 - 1) * var(group1, na.rm = TRUE) + 
                     (n2 - 1) * var(group2, na.rm = TRUE)) / (n1 + n2 - 2))
  if (pooled_sd == 0) return(0)
  (mean(group1, na.rm = TRUE) - mean(group2, na.rm = TRUE)) / pooled_sd
}

# Effect size classification
classify_effect_size <- function(d) {
  abs_d <- abs(d)
  if (abs_d < 0.2) return("negligible")
  if (abs_d < 0.5) return("small")
  if (abs_d < 0.8) return("medium")
  return("large")
}
