# ============================================================================
# cgm_processor.R - Unified CGM Data Processing (R Implementation)
# ============================================================================

library(dplyr)
library(tidyr)
library(lubridate)
library(zoo)

# Unified CGM processor for multiple device types
process_cgm_unified <- function(csv_path, device_type) {
  supported_devices <- c("dexcom_g7", "dexcom_g6", "libre_3", "libre_2", "medtronic_g4")

  if (!device_type %in% supported_devices) {
    stop(paste("Unsupported device:", device_type))
  }

  # Parse based on device type
  raw <- switch(device_type,
    "dexcom_g7" = read.csv(csv_path) %>%
      rename(timestamp_raw = Timestamp, glucose_raw = Glucose.Value..mg.dL.),
    "dexcom_g6" = read.csv(csv_path) %>%
      rename(timestamp_raw = Timestamp, glucose_raw = Glucose.Value..mg.dL.),
    "libre_3" = read.csv(csv_path, skip = 1) %>%
      rename(timestamp_raw = Device.Timestamp, glucose_raw = Historic.Glucose..mg.dL.),
    "libre_2" = read.csv(csv_path, skip = 1) %>%
      rename(timestamp_raw = Device.Timestamp, glucose_raw = Historic.Glucose..mg.dL.),
    "medtronic_g4" = read.csv(csv_path) %>%
      rename(timestamp_raw = Date, glucose_raw = Sensor.Glucose..mg.dL.)
  )

  # Standardize
  standardized <- raw %>%
    mutate(
      timestamp = parse_date_time(
        timestamp_raw,
        orders = c("Ymd HM", "Ymd HMS", "mdy HM", "mdy HMS", "ymd HM", "ymd HMS"),
        tz = "UTC"
      ),
      glucose_mgdl = as.numeric(glucose_raw),
      device_type = device_type
    ) %>%
    select(timestamp, glucose_mgdl, device_type) %>%
    arrange(timestamp)

  # Quality control
  qc <- standardized %>%
    mutate(
      qc_flag = case_when(
        glucose_mgdl < 40 | glucose_mgdl > 400 ~ "impossible",
        glucose_mgdl < 70 | glucose_mgdl > 180 ~ "out_of_target",
        TRUE ~ "valid"
      )
    ) %>%
    filter(qc_flag != "impossible") %>%
    distinct(timestamp, .keep_all = TRUE)

  # Gap filling (linear interpolation for gaps <= 15 min)
  qc <- qc %>%
    complete(timestamp = seq(min(timestamp), max(timestamp), by = "5 min")) %>%
    mutate(
      gap_minutes = as.numeric(difftime(timestamp, lag(timestamp), units = "mins")),
      gap_flag = gap_minutes > 15
    ) %>%
    mutate(glucose_mgdl = zoo::na.approx(glucose_mgdl, maxgap = 3, na.rm = FALSE)) %>%
    filter(!is.na(glucose_mgdl))

  return(qc)
}

# Advanced glycemic metrics
compute_advanced_metrics <- function(cgm_df) {
  glucose <- cgm_df$glucose_mgdl
  n <- length(glucose)

  if (n == 0) return(list())

  mean_glucose <- mean(glucose, na.rm = TRUE)
  sd_glucose <- sd(glucose, na.rm = TRUE)
  cv <- (sd_glucose / mean_glucose) * 100

  tir <- mean(glucose >= 70 & glucose <= 180, na.rm = TRUE) * 100
  titr <- mean(glucose >= 70 & glucose <= 140, na.rm = TRUE) * 100
  tbr <- mean(glucose < 70, na.rm = TRUE) * 100
  tar <- mean(glucose > 180, na.rm = TRUE) * 100
  tvr <- mean(glucose > 250, na.rm = TRUE) * 100

  gmi <- 3.31 + (0.02392 * mean_glucose)
  gri <- (3.0 * tbr) + (1.6 * tar)

  excursions <- abs(diff(glucose))
  mage <- mean(excursions[excursions > sd_glucose], na.rm = TRUE)
  if (is.na(mage) || is.nan(mage)) mage <- 0

  total_days <- as.numeric(difftime(max(cgm_df$timestamp), min(cgm_df$timestamp), units = "days")) + 1
  expected_readings <- total_days * 288
  wear_time <- (n / expected_readings) * 100

  return(list(
    n_readings = n,
    total_days = total_days,
    wear_time_pct = round(wear_time, 1),
    mean_glucose = round(mean_glucose, 1),
    sd_glucose = round(sd_glucose, 1),
    cv = round(cv, 1),
    cv_category = ifelse(cv < 36, "Stable", "Unstable"),
    tir = round(tir, 1),
    titr = round(titr, 1),
    tbr = round(tbr, 1),
    tar = round(tar, 1),
    tvr = round(tvr, 1),
    gmi = round(gmi, 1),
    gri = round(gri, 1),
    mage = round(mage, 1)
  ))
}
