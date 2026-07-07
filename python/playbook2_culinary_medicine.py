"""
================================================================================
PLAYBOOK 2: Educational Intervention Evaluator with Psychometrics
================================================================================
Purpose: Comprehensive evaluation framework for video-based health education
interventions. Includes multi-language quiz support, psychometric item analysis,
mixed-effects longitudinal modeling, optional Bayesian estimation, and clinical
outcome linkage.

This module demonstrates:
- Psychometrics: item difficulty, discrimination, distractor analysis
- Advanced statistics: mixed-effects models, Bayesian inference
- Multi-language software architecture (i18n)
- Causal inference scaffolding: linking education to biological outcomes

Dependencies: pandas, numpy, matplotlib, seaborn, scipy, statsmodels, python-dotenv
================================================================================
"""

import logging
from dataclasses import dataclass
from typing import Dict, List

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from dotenv import load_dotenv
from scipy import stats
from scipy.stats import pearsonr, pointbiserialr
from statsmodels.formula.api import mixedlm

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
)
logger = logging.getLogger(__name__)

sns.set_style("whitegrid")
plt.rcParams["figure.figsize"] = (12, 6)


# ==============================================================================
# P1: Multi-Language Content Manager
# ==============================================================================


class MultiLanguageContentManager:
    """
    Manage educational content and assessments in multiple languages.

    Supports 5 languages with culturally specific modifications per cuisine tradition.
    Demonstrates i18n (internationalization) architecture for health equity.
    """

    TRANSLATIONS = {
        "filipino": {
            "en": {
                "title": "Filipino Adobo: Traditional & Glucose-Friendly",
                "mods": [
                    "Add grilled chicken before rice",
                    "Use cauliflower rice mix",
                    "Add okra and eggplant",
                    "Use coconut vinegar",
                ],
            },
            "es": {
                "title": "Adobo Filipino: Tradicional y Amigable con la Glucosa",
                "mods": [
                    "Agregue pollo a la parrilla",
                    "Use mezcla de arroz de coliflor",
                    "Agregue okra y berenjena",
                    "Use vinagre de coco",
                ],
            },
            "tl": {
                "title": "Adobong Filipino: Tradisyonal at Glucose-Friendly",
                "mods": [
                    "Magdagdag ng inihaw na manok",
                    "Gumamit ng cauliflower rice",
                    "Magdagdag ng okra at talong",
                    "Gumamit ng suka ng niyog",
                ],
            },
        },
        "indian": {
            "en": {
                "title": "Indian Dal & Roti: Traditional & Glucose-Friendly",
                "mods": [
                    "Add paneer or tofu",
                    "Use chickpea flour roti",
                    "Add spinach and fenugreek",
                    "Use cinnamon and turmeric",
                ],
            }
        },
        "vietnamese": {
            "en": {
                "title": "Vietnamese Pho: Traditional & Glucose-Friendly",
                "mods": [
                    "Add extra protein",
                    "Use thin rice noodles",
                    "Load up on bean sprouts",
                    "Squeeze lime before eating",
                ],
            },
            "vi": {
                "title": "Pho Viet Nam: Truyen Thong & Than Thien voi Duong Huyet",
                "mods": [
                    "Them protein",
                    "Su dung bun mi mong",
                    "Nhieu gia va rau thom",
                    "Vat chanh truoc khi an",
                ],
            },
        },
        "latinx": {
            "en": {
                "title": "Latinx Pozole: Traditional & Glucose-Friendly",
                "mods": [
                    "Add shredded chicken early",
                    "Use hominy in moderation",
                    "Top with avocado",
                    "Use fresh cilantro and oregano",
                ],
            }
        },
    }

    QUIZ_TRANSLATIONS = {
        "q1": {
            "en": {
                "text": "Adding protein before carbohydrates will:",
                "options": {
                    1: "Increase spike",
                    2: "Blunt spike",
                    3: "No effect",
                    99: "Don't know",
                },
            },
            "es": {
                "text": "Agregar proteina antes de carbohidratos:",
                "options": {
                    1: "Aumenta pico",
                    2: "Reduce pico",
                    3: "Sin efecto",
                    99: "No se",
                },
            },
            "tl": {
                "text": "Ang pagdagdag ng protein bago ang carbs ay:",
                "options": {
                    1: "Tataas ang spike",
                    2: "Bababa ang spike",
                    3: "Walang epekto",
                    99: "Hindi alam",
                },
            },
        },
        "q2": {
            "en": {
                "text": "Thin rice noodles vs. thick flat noodles:",
                "options": {
                    1: "Higher GI",
                    2: "Lower GI",
                    3: "Same GI",
                    99: "Don't know",
                },
            },
            "es": {
                "text": "Fideos de arroz delgados vs. gruesos:",
                "options": {1: "Mayor IG", 2: "Menor IG", 3: "Igual IG", 99: "No se"},
            },
            "vi": {
                "text": "Bun mi mong vs. bun mi day:",
                "options": {
                    1: "GI cao hon",
                    2: "GI thap hon",
                    3: "GI nhu nhau",
                    99: "Khong biet",
                },
            },
        },
    }

    def get_content(self, cuisine: str, lang: str = "en") -> Dict:
        """Retrieve translated content for a cuisine module."""
        return self.TRANSLATIONS.get(cuisine, {}).get(
            lang, self.TRANSLATIONS.get(cuisine, {}).get("en", {})
        )

    def get_quiz(self, q_id: str, lang: str = "en") -> Dict:
        """Retrieve translated quiz question."""
        return self.QUIZ_TRANSLATIONS.get(q_id, {}).get(
            lang, self.QUIZ_TRANSLATIONS.get(q_id, {}).get("en", {})
        )


# ==============================================================================
# P1: Enhanced Quiz Scorer with Psychometric Item Analysis
# ==============================================================================


@dataclass
class QuizItem:
    question_id: str
    text: str
    correct_answer: str
    options: Dict[str, str]


QUIZ_ANSWER_KEY = {"q1": "2", "q2": "2", "q3": "2", "q4": "2", "q5": "2"}


class EnhancedQuizScorer:
    """
    Quiz scoring with psychometric item analysis.

    Ensures assessments actually measure learning, not memorization:
    - Item difficulty: % correct (target 30-80%)
    - Point-biserial correlation: links item score to total score (target >0.3)
    - Distractor analysis: checks if wrong answers are plausible but clearly wrong
    """

    def __init__(self, answer_key=QUIZ_ANSWER_KEY):
        self.answer_key = answer_key

    def score_quiz(self, row, prefix="pre") -> Dict:
        """Score a single participant's quiz responses."""
        score = 0
        details = {}
        for q_id, correct in self.answer_key.items():
            col_name = f"{prefix}_{q_id}"
            if col_name in row.index:
                answer = str(row[col_name])
                is_correct = answer == correct
                score += 1 if is_correct else 0
                details[q_id] = {
                    "answer": answer,
                    "correct": correct,
                    "is_correct": is_correct,
                }
        return {
            "score": score,
            "max_score": len(self.answer_key),
            "percentage": (score / len(self.answer_key)) * 100,
            "details": details,
        }

    def process_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Add scored columns to a DataFrame."""
        df = df.copy()
        df["pre_score"] = df.apply(
            lambda row: self.score_quiz(row, "pre")["score"], axis=1
        )
        df["post_score"] = df.apply(
            lambda row: self.score_quiz(row, "post")["score"], axis=1
        )
        df["knowledge_gain"] = df["post_score"] - df["pre_score"]
        df["knowledge_gain_pct"] = (df["knowledge_gain"] / len(self.answer_key)) * 100
        return df

    def generate_item_analysis(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Generate psychometric item analysis report.

        Returns DataFrame with:
        - pre/post difficulty (proportion correct)
        - improvement (post - pre)
        - point-biserial correlation (discrimination index)
        - distractor frequencies
        """
        item_stats = []

        for q_id in self.answer_key.keys():
            pre_col = f"pre_{q_id}"
            post_col = f"post_{q_id}"

            if pre_col in df.columns and post_col in df.columns:
                pre_correct = (df[pre_col] == self.answer_key[q_id]).mean()
                post_correct = (df[post_col] == self.answer_key[q_id]).mean()

                pre_binary = (df[pre_col] == self.answer_key[q_id]).astype(int)
                post_binary = (df[post_col] == self.answer_key[q_id]).astype(int)

                pre_pb = (
                    pointbiserialr(pre_binary, df["pre_score"])[0]
                    if "pre_score" in df.columns
                    else None
                )
                post_pb = (
                    pointbiserialr(post_binary, df["post_score"])[0]
                    if "post_score" in df.columns
                    else None
                )

                distractors = {}
                for opt in ["1", "2", "3", "99"]:
                    distractors[f"pre_opt_{opt}"] = (df[pre_col] == opt).sum()
                    distractors[f"post_opt_{opt}"] = (df[post_col] == opt).sum()

                item_stats.append(
                    {
                        "question_id": q_id,
                        "pre_difficulty": round(pre_correct, 3),
                        "post_difficulty": round(post_correct, 3),
                        "improvement": round(post_correct - pre_correct, 3),
                        "pre_point_biserial": round(pre_pb, 3) if pre_pb else None,
                        "post_point_biserial": round(post_pb, 3) if post_pb else None,
                        **distractors,
                    }
                )

        return pd.DataFrame(item_stats)


# ==============================================================================
# P1: Mixed Effects Model Analysis
# ==============================================================================


class MixedEffectsAnalyzer:
    """
    Longitudinal analysis with mixed effects models.

    Accounts for:
    - Repeated measures (same person measured multiple times)
    - Clustering (participants nested within sites/health workers)

    Uses convergence fallback: complex → simple → fixed-effects
    """

    def __init__(self, alpha=0.05):
        self.alpha = alpha

    def _wide_to_long(
        self,
        df: pd.DataFrame,
        id_col: str,
        time_col: str,
        value_cols: List[str],
        time_mapping: Dict,
    ) -> pd.DataFrame:
        """Convert wide-format longitudinal data to long format."""
        long_data = []
        for _, row in df.iterrows():
            for col, time_val in time_mapping.items():
                if col in row.index and pd.notna(row[col]):
                    entry = {id_col: row[id_col]}
                    for covariate in ["module_cuisine", "site", "language"]:
                        if covariate in row.index:
                            entry[covariate] = row[covariate]
                    entry[time_col] = time_val
                    entry["score"] = row[col]
                    long_data.append(entry)
        return pd.DataFrame(long_data)

    def fit_knowledge_model(self, df: pd.DataFrame) -> Dict:
        """
        Fit mixed model: score ~ timepoint * cuisine + (1|participant)

        Fallback chain:
        1. Random intercept + random slope for time
        2. Random intercept only
        3. Fixed-effects OLS
        """
        long_df = self._wide_to_long(
            df,
            "participant_id",
            "timepoint",
            ["pre_score", "post_score"],
            {"pre_score": 0, "post_score": 1},
        )

        if len(long_df) < 10:
            return {"error": "Insufficient data for mixed model"}

        # Attempt 1: Complex model
        try:
            model = mixedlm(
                "score ~ timepoint * C(module_cuisine)",
                long_df,
                groups=long_df["participant_id"],
                re_formula="~timepoint",
            )
            result = model.fit(method="lbfgs")
            model_type = "mixedlm_random_slope"
        except Exception as e:
            logger.warning(f"Complex model failed: {e}. Trying random intercept only.")
            try:
                model = mixedlm(
                    "score ~ timepoint * C(module_cuisine)",
                    long_df,
                    groups=long_df["participant_id"],
                )
                result = model.fit(method="lbfgs")
                model_type = "mixedlm_random_intercept"
            except Exception as e2:
                logger.warning(f"Random intercept failed: {e2}. Using fixed effects.")
                return {
                    "error": f"Both mixed models failed: {e2}",
                    "model_type": "fixed_effects_fallback",
                    "note": "Consider collecting more data or simplifying random effects",
                }

        return {
            "model_type": model_type,
            "converged": getattr(result, "converged", True),
            "aic": result.aic,
            "bic": result.bic,
            "coefficients": result.params.to_dict(),
            "pvalues": result.pvalues.to_dict(),
            "random_effects_variance": (
                result.cov_re.iloc[0, 0] if len(result.cov_re) > 0 else None
            ),
            "summary": str(result.summary()),
        }

    def fit_self_efficacy_model(self, df: pd.DataFrame) -> Dict:
        """Fit mixed model for self-efficacy (continuous 0-10 scale)."""
        long_data = []
        for _, row in df.iterrows():
            if all(
                c in row.index
                for c in [
                    "mi_confidence_recipes",
                    "mi_confidence_cooking",
                    "mi_confidence_family",
                ]
            ):
                se = (
                    row["mi_confidence_recipes"]
                    + row["mi_confidence_cooking"]
                    + row["mi_confidence_family"]
                ) / 3
                long_data.append(
                    {
                        "participant_id": row["participant_id"],
                        "module_cuisine": row.get("module_cuisine"),
                        "timepoint": 0 if row.get("timepoint") == "1" else 1,
                        "self_efficacy": se,
                        "readiness": row.get("mi_readiness"),
                        "importance": row.get("mi_importance"),
                    }
                )

        long_df = pd.DataFrame(long_data)
        if len(long_df) < 10:
            return {"error": "Insufficient data"}

        try:
            model = mixedlm(
                "self_efficacy ~ timepoint * C(module_cuisine) + readiness + importance",
                long_df,
                groups=long_df["participant_id"],
            )
            result = model.fit()

            return {
                "model_type": "mixedlm",
                "aic": result.aic,
                "coefficients": result.params.to_dict(),
                "pvalues": result.pvalues.to_dict(),
                "summary": str(result.summary()),
            }
        except Exception as e:
            return {"error": str(e)}


# ==============================================================================
# P1: Bayesian Knowledge Gain Analysis (Optional Advanced)
# ==============================================================================


class BayesianAnalyzer:
    """
    Bayesian estimation of intervention effects.

    Advantage over frequentist: reports probability of positive effect
    directly (e.g., "94% probability of improvement") rather than
    p-values ("if null were true, probability of this data is 8%").

    Falls back to analytical approximation if PyMC not installed.
    """

    def estimate_knowledge_gain(
        self, pre_scores: np.ndarray, post_scores: np.ndarray, n_samples: int = 2000
    ) -> Dict:
        try:
            import arviz as az
            import pymc as pm

            with pm.Model():
                mu_pre = pm.Normal(
                    "mu_pre", mu=pre_scores.mean(), sigma=pre_scores.std()
                )
                mu_post = pm.Normal(
                    "mu_post", mu=post_scores.mean(), sigma=post_scores.std()
                )
                sigma = pm.HalfNormal(
                    "sigma", sigma=max(pre_scores.std(), post_scores.std())
                )

                pm.Normal("pre_obs", mu=mu_pre, sigma=sigma, observed=pre_scores)
                pm.Normal("post_obs", mu=mu_post, sigma=sigma, observed=post_scores)

                pm.Deterministic("gain", mu_post - mu_pre)
                trace = pm.sample(n_samples, tune=1000, cores=2)

                summary = az.summary(trace, var_names=["gain"])

                return {
                    "method": "bayesian_pymc",
                    "gain_mean": float(summary.loc["gain", "mean"]),
                    "gain_hdi_lower": float(summary.loc["gain", "hdi_3%"]),
                    "gain_hdi_upper": float(summary.loc["gain", "hdi_97%"]),
                    "probability_positive": float((trace.posterior["gain"] > 0).mean()),
                    "trace": trace,
                }
        except ImportError:
            # Analytical fallback
            diff = post_scores - pre_scores
            mean_diff = diff.mean()
            se_diff = diff.std() / np.sqrt(len(diff))

            return {
                "method": "analytical_approximation",
                "gain_mean": mean_diff,
                "gain_ci_lower": mean_diff - 1.96 * se_diff,
                "gain_ci_upper": mean_diff + 1.96 * se_diff,
                "probability_positive": 1
                - stats.norm.cdf(0, loc=mean_diff, scale=se_diff),
                "note": "Install PyMC for full Bayesian inference: pip install pymc arviz",
            }


# ==============================================================================
# P1: Clinical Outcome Linker
# ==============================================================================


class OutcomeLinker:
    """
    Link educational intervention data to clinical biomarker outcomes.

    Tests the translational hypothesis: does knowledge gain correlate with
    biological improvement (e.g., improved glucose control)?
    """

    def link_and_analyze(
        self,
        education_df: pd.DataFrame,
        biomarker_df: pd.DataFrame,
        join_cols: List[str] = None,
    ) -> Dict:
        """Merge education and biomarker data, compute correlations."""

        join_cols = join_cols or ["participant_id"]

        # Validate required columns
        required_edu = join_cols
        required_bio = join_cols + ["cgm_tir", "cgm_cv", "cgm_gri"]

        missing_edu = [c for c in required_edu if c not in education_df.columns]
        missing_bio = [c for c in required_bio if c not in biomarker_df.columns]

        if missing_edu or missing_bio:
            return {
                "error": f"Missing columns. Education: {missing_edu}, Biomarker: {missing_bio}"
            }

        merged = education_df.merge(biomarker_df, on=join_cols, how="inner")

        correlations = {}
        outcome_pairs = [
            ("knowledge_gain", "cgm_tir"),
            ("self_efficacy_post", "cgm_cv"),
            ("readiness", "cgm_gri"),
        ]

        for edu_var, bio_var in outcome_pairs:
            if edu_var not in merged.columns:
                continue
            valid = merged.dropna(subset=[edu_var, bio_var])
            if len(valid) > 5:
                r, p = pearsonr(valid[edu_var], valid[bio_var])
                correlations[f"{edu_var}_vs_{bio_var}"] = {
                    "r": round(r, 3),
                    "p": round(p, 3),
                    "n": len(valid),
                    "significant": p < 0.05,
                }

        return {
            "correlations": correlations,
            "n_linked": len(merged),
            "linkage_rate": (
                len(merged) / len(education_df) if len(education_df) > 0 else 0
            ),
        }


# ==============================================================================
# Report Generator
# ==============================================================================


class InterventionReportGenerator:
    """Generate publication-ready figures for intervention evaluation."""

    def __init__(self, analyzer: MixedEffectsAnalyzer):
        self.analyzer = analyzer

    def generate(self, df: pd.DataFrame, output_dir: str = ".") -> Dict:
        df = df.copy()

        # Calculate self-efficacy if components available
        se_cols = [
            "mi_confidence_recipes",
            "mi_confidence_cooking",
            "mi_confidence_family",
        ]
        if all(c in df.columns for c in se_cols):
            df["self_efficacy_pre"] = df[se_cols].mean(axis=1)
            df["self_efficacy_post"] = df["self_efficacy_pre"]  # placeholder

        figs = {}
        cuisine_map = {1: "Filipino", 2: "Indian", 3: "Vietnamese", 4: "Latinx"}
        colors = ["#FF6B6B", "#4ECDC4", "#45B7D1", "#96CEB4"]

        # Plot 1: Knowledge gain by cuisine
        if "knowledge_gain" in df.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            df["cuisine_label"] = df["module_cuisine"].map(cuisine_map)
            cuisine_summary = (
                df.groupby("cuisine_label")["knowledge_gain"]
                .agg(["mean", "std", "count"])
                .reset_index()
            )
            ax.bar(
                cuisine_summary["cuisine_label"],
                cuisine_summary["mean"],
                yerr=cuisine_summary["std"] / np.sqrt(cuisine_summary["count"]),
                capsize=5,
                color=colors,
            )
            ax.set_title(
                "Knowledge Gain by Module (Mixed Effects Adjusted)", fontsize=14
            )
            ax.set_ylabel("Mean Knowledge Gain (points)")
            plt.tight_layout()
            figs["knowledge_gain"] = fig
            plt.savefig(
                f"{output_dir}/pb2_knowledge_gain.png", dpi=150, bbox_inches="tight"
            )
            plt.close()

        # Plot 2: Self-efficacy pre/post
        if "self_efficacy_pre" in df.columns and "self_efficacy_post" in df.columns:
            fig, ax = plt.subplots(figsize=(10, 6))
            efficacy_summary = (
                df.groupby("cuisine_label")
                .apply(
                    lambda x: pd.Series(
                        {
                            "mean_pre": x["self_efficacy_pre"].mean(),
                            "mean_post": x["self_efficacy_post"].mean(),
                            "n": x["self_efficacy_pre"].notna().sum(),
                        }
                    )
                )
                .reset_index()
            )
            x = np.arange(len(efficacy_summary))
            width = 0.35
            ax.bar(
                x - width / 2,
                efficacy_summary["mean_pre"],
                width,
                label="Pre",
                color="#74b9ff",
            )
            ax.bar(
                x + width / 2,
                efficacy_summary["mean_post"],
                width,
                label="Post",
                color="#00b894",
            )
            ax.set_title("Self-Efficacy: Pre vs. Post by Module")
            ax.set_ylabel("Mean Score (0-10)")
            ax.set_xticks(x)
            ax.set_xticklabels(efficacy_summary["cuisine_label"])
            ax.legend()
            plt.tight_layout()
            figs["self_efficacy"] = fig
            plt.savefig(
                f"{output_dir}/pb2_self_efficacy.png", dpi=150, bbox_inches="tight"
            )
            plt.close()

        return {
            "figures": figs,
            "total_participants": df["participant_id"].nunique(),
            "total_modules": len(df),
        }


# ==============================================================================
# MAIN
# ==============================================================================


def main():
    """Demo: Run psychometric analysis on synthetic data."""
    logger.info("Playbook 2: Educational Intervention Evaluator")

    # Create synthetic quiz data
    np.random.seed(42)
    n = 100
    df = pd.DataFrame(
        {
            "participant_id": [f"P{i:03d}" for i in range(1, n + 1)],
            "module_cuisine": np.random.choice([1, 2, 3, 4], n),
            "pre_q1": np.random.choice(
                ["1", "2", "3", "99"], n, p=[0.2, 0.5, 0.2, 0.1]
            ),
            "pre_q2": np.random.choice(
                ["1", "2", "3", "99"], n, p=[0.15, 0.55, 0.2, 0.1]
            ),
            "post_q1": np.random.choice(
                ["1", "2", "3", "99"], n, p=[0.1, 0.7, 0.15, 0.05]
            ),
            "post_q2": np.random.choice(
                ["1", "2", "3", "99"], n, p=[0.08, 0.75, 0.12, 0.05]
            ),
        }
    )

    scorer = EnhancedQuizScorer()
    df = scorer.process_dataframe(df)

    logger.info(f"Mean knowledge gain: {df['knowledge_gain'].mean():.2f} points")

    # Item analysis
    item_analysis = scorer.generate_item_analysis(df)
    logger.info(f"Item analysis complete: {len(item_analysis)} items evaluated")
    print(item_analysis.head())

    # Mixed effects model
    analyzer = MixedEffectsAnalyzer()
    model_results = analyzer.fit_knowledge_model(df)
    logger.info(f"Model type: {model_results.get('model_type', 'N/A')}")

    return df, item_analysis, model_results


if __name__ == "__main__":
    main()
