# ============================================================================
# PLAYBOOK 3 (R): Implementation Science Dashboard
# ============================================================================

library(shiny)
library(shinydashboard)
library(plotly)
library(DT)
library(dplyr)

source("src/utils.R")

# Shiny UI
cat("Playbook 3 (R): Implementation Science Dashboard\n")
cat("Run with: shinyApp(ui = ui, server = server)\n")
