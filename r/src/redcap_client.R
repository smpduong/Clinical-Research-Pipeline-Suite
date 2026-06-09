# ============================================================================
# redcap_client.R - Secure REDCap API Client (R Implementation)
# ============================================================================

library(REDCapR)
library(digest)

REDCAP_URI <- Sys.getenv("REDCAP_URI", "https://your-institution.redcap.edu/api/")
API_TOKEN <- Sys.getenv("REDCAP_API_TOKEN")

# Retry wrapper for API calls
api_call_with_retry <- function(data, max_retries = 3, backoff = 2) {
  for (attempt in 1:max_retries) {
    result <- tryCatch({
      redcap_read(redcap_uri = REDCAP_URI, token = API_TOKEN, 
                  fields = data$fields, records = data$records)
    }, error = function(e) list(data = data.frame(), success = FALSE, error = conditionMessage(e)))

    if (result$success && nrow(result$data) > 0) {
      return(result$data)
    }
    if (attempt == max_retries) {
      warning(paste("Failed after", max_retries, "attempts:", result$error))
      return(data.frame())
    }
    Sys.sleep(backoff ^ attempt)
  }
}

# HIPAA audit logging
log_audit <- function(action, record_id, field = "", old_val = NULL, 
                      new_val = NULL, reason = "", log_path = "audit.log") {
  if (!file.exists(log_path)) {
    write.table(
      data.frame(timestamp = character(), action = character(), record_id = character(),
                   field = character(), old_hash = character(), new_hash = character(),
                   reason = character(), stringsAsFactors = FALSE),
      log_path, sep = "|", row.names = FALSE, col.names = TRUE
    )
  }

  entry <- data.frame(
    timestamp = format(Sys.time(), "%Y-%m-%d %H:%M:%S"),
    action = action,
    record_id = record_id,
    field = field,
    old_hash = ifelse(is.null(old_val), "", digest::digest(old_val)),
    new_hash = ifelse(is.null(new_val), "", digest::digest(new_val)),
    reason = reason,
    stringsAsFactors = FALSE
  )
  write.table(entry, log_path, append = TRUE, sep = "|", 
              row.names = FALSE, col.names = FALSE)
}
