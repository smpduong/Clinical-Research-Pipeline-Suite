# ============================================================================
# test_cgm_processor.R - Unit Tests for R CGM Processor
# ============================================================================

library(testthat)

source("../src/cgm_processor.R")

test_that("CGM processor handles supported devices", {
  expect_error(process_cgm_unified("dummy.csv", "unsupported"), "Unsupported device")
})

test_that("Metrics computed correctly for known values", {
  df <- data.frame(
    timestamp = seq(as.POSIXct("2026-01-01"), by = "5 min", length.out = 288),
    glucose_mgdl = c(rep(60, 10), rep(100, 268), rep(200, 10)),
    device_type = "dexcom_g7"
  )
  metrics <- compute_advanced_metrics(df)
  expect_equal(metrics$tir, round(268/288 * 100, 1))
  expect_equal(metrics$tbr, round(10/288 * 100, 1))
  expect_equal(metrics$tar, round(10/288 * 100, 1))
})

test_that("Cohen's d calculation works", {
  g1 <- rnorm(50, mean = 100, sd = 15)
  g2 <- rnorm(50, mean = 110, sd = 15)
  d <- cohens_d(g1, g2)
  expect_true(abs(d) > 0.5 && abs(d) < 0.8)
})
