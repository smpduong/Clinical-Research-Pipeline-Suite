# ============================================================================
# PLAYBOOK 2 (R): Educational Intervention Evaluator
# ============================================================================

library(dplyr)
library(tidyr)
library(lme4)
library(lmerTest)
library(emmeans)

source("src/utils.R")

# Mixed effects model with convergence fallback
fit_mixed_model <- function(data, formula_str, random_effect) {
  model <- NULL
  convergence_ok <- FALSE

  tryCatch({
    model <- lmer(as.formula(formula_str), data = data, REML = TRUE)
    convergence_ok <- TRUE
  }, error = function(e) {
    message("Complex model failed: ", conditionMessage(e))
  })

  if (!convergence_ok) {
    tryCatch({
      # Drop the random-effects term, e.g. "+ (1 | id)", for the fixed-effects fallback
      simple_formula <- gsub("\\s*\\+\\s*\\(1\\s*\\|[^)]*\\)", "", formula_str)
      model <- lm(as.formula(simple_formula), data = data)
      message("Using fixed-effects fallback")
    }, error = function(e2) {
      message("Even fixed effects failed: ", conditionMessage(e2))
    })
  }

  return(list(model = model, convergence = convergence_ok))
}

cat("Playbook 2 (R): Educational Intervention Evaluator\n")
cat("Fit models with: fit_mixed_model(data, 'score ~ time * cuisine + (1|id)', 'id')\n")
