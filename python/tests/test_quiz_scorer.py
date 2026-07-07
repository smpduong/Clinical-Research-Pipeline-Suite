"""
test_quiz_scorer.py - Unit tests for quiz scoring and psychometrics
"""

import numpy as np
import pandas as pd
import pytest


class TestQuizScorer:
    """Tests for quiz scoring functionality (extracted from playbook2)."""

    def test_score_calculation(self):
        answer_key = {"q1": "2", "q2": "2", "q3": "2"}
        responses = {"pre_q1": "2", "pre_q2": "1", "pre_q3": "2"}

        score = sum(
            1 for q, ans in answer_key.items() if responses.get(f"pre_{q}") == ans
        )
        assert score == 2
        assert score / len(answer_key) * 100 == pytest.approx(66.67, rel=0.01)

    def test_item_difficulty_calculation(self):
        """Item difficulty = proportion correct. Target: 0.30-0.80."""
        answers = pd.Series(["2", "2", "1", "2", "3", "3", "1", "2"])
        correct = "2"
        difficulty = (answers == correct).mean()
        assert difficulty == 0.5  # 4/8 correct
        assert 0.3 <= difficulty <= 0.8  # Within acceptable range

    def test_point_biserial_correlation(self):
        """Point-biserial: correlation between item score and total score."""
        from scipy.stats import pointbiserialr

        # 10 participants
        item_correct = np.array([1, 1, 1, 0, 1, 0, 1, 1, 0, 1])  # binary
        total_scores = np.array([5, 4, 5, 2, 4, 3, 5, 4, 2, 4])

        r, p = pointbiserialr(item_correct, total_scores)
        assert r > 0.3  # Good discriminating item
        assert p < 0.05  # Statistically significant


class TestEffectSizeCalculation:
    """Tests for Cohen's d and effect size classification."""

    def test_cohens_d_small_effect(self):
        from src.utils import cohens_d

        # Mean difference of 0.5 with pooled SD ~1.58 -> |d| ~= 0.32
        group1 = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        group2 = np.array([0.5, 1.5, 2.5, 3.5, 4.5])
        d = cohens_d(group1, group2)
        assert abs(d) < 0.5  # Small effect

    def test_cohens_d_medium_effect(self):
        from src.utils import cohens_d

        # Mean difference of 1.0 with pooled SD ~1.58 -> |d| ~= 0.63
        group1 = np.array([0.0, 1.0, 2.0, 3.0, 4.0])
        group2 = np.array([1.0, 2.0, 3.0, 4.0, 5.0])
        d = cohens_d(group1, group2)
        assert 0.5 <= abs(d) < 0.8  # Medium effect

    def test_effect_size_classification(self):
        from src.utils import classify_effect_size

        assert classify_effect_size(0.1) == "negligible"
        assert classify_effect_size(0.3) == "small"
        assert classify_effect_size(0.6) == "medium"
        assert classify_effect_size(1.0) == "large"
