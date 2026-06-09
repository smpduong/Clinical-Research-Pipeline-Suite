# ============================================================================
# PLAYBOOK 1 (R): Multi-Device CGM & Cultural Meal Tracker
# ============================================================================

library(dplyr)
library(tidyr)
library(ggplot2)
library(lubridate)

source("src/cgm_processor.R")
source("src/redcap_client.R")
source("src/utils.R")

# Main execution
cat("Playbook 1 (R): CGM & Cultural Meal Tracker\n")
cat("Load data with: process_cgm_unified('data.csv', 'dexcom_g7')\n")
cat("Compute metrics with: compute_advanced_metrics(cgm_df)\n")
