"""
================================================================================
PLAYBOOK 1: Multi-Device CGM & Cultural Meal Tracker
================================================================================
Purpose: Unified pipeline for processing continuous glucose monitor (CGM) data
from multiple device manufacturers, linking it to culturally specific meal logs,
and generating automated weekly glycemic reports.

This module demonstrates:
- Data engineering: multi-source ingestion, standardization, quality control
- Clinical domain expertise: glycemic metrics per ADA standards
- Automated reporting: publication-ready visualizations
- Regulatory awareness: HIPAA audit trails, data validation

Dependencies: pandas, numpy, matplotlib, seaborn, scipy, python-dotenv
================================================================================
"""

import os
import sys
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from scipy import stats
from dotenv import load_dotenv

# Import shared modules
from src.cgm_processor import UnifiedCGMProcessor
from src.redcap_client import SecureREDCapClient
from src.utils import cohens_d, classify_effect_size

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)-8s | %(name)s | %(message)s'
)
logger = logging.getLogger(__name__)

sns.set_style("whitegrid")
plt.rcParams['figure.figsize'] = (12, 6)


# ==============================================================================
# P1: Cultural Food Library & Estimated Glycemic Load Engine
# ==============================================================================

@dataclass
class FoodItem:
    """Nutritional profile for a culturally specific dish."""
    name: str
    gi: float           # Glycemic index (0-100)
    carbs_per_serving: float
    cuisine: str
    protein_g: float = 0.0
    fiber_g: float = 0.0


# Database of 32 dishes across 4 cuisine traditions
# Sources: USDA FoodData Central, international GI databases
FOOD_LIBRARY: Dict[str, Dict[str, FoodItem]] = {
    "filipino": {
        "adobo": FoodItem("Adobo", 45, 15, "filipino", 25, 2),
        "sinigang": FoodItem("Sinigang", 35, 12, "filipino", 20, 3),
        "pancit": FoodItem("Pancit", 55, 35, "filipino", 8, 2),
        "lumpia": FoodItem("Lumpia", 60, 20, "filipino", 5, 1),
        "tapsilog": FoodItem("Tapsilog", 70, 45, "filipino", 15, 1),
        "kare_kare": FoodItem("Kare-Kare", 40, 18, "filipino", 18, 4),
        "lechon": FoodItem("Lechon", 0, 0, "filipino", 30, 0),
        "halo_halo": FoodItem("Halo-Halo", 65, 55, "filipino", 5, 2),
    },
    "indian": {
        "dal": FoodItem("Dal", 30, 20, "indian", 12, 8),
        "chana_masala": FoodItem("Chana Masala", 35, 25, "indian", 14, 10),
        "biryani": FoodItem("Biryani", 60, 50, "indian", 10, 3),
        "roti": FoodItem("Roti", 65, 30, "indian", 6, 4),
        "saag_paneer": FoodItem("Saag Paneer", 25, 10, "indian", 15, 5),
        "tandoori_chicken": FoodItem("Tandoori Chicken", 0, 0, "indian", 35, 0),
        "samosa": FoodItem("Samosa", 70, 25, "indian", 4, 2),
        "kheer": FoodItem("Kheer", 65, 40, "indian", 6, 0),
    },
    "vietnamese": {
        "pho": FoodItem("Pho", 50, 40, "vietnamese", 18, 2),
        "banh_mi": FoodItem("Banh Mi", 65, 45, "vietnamese", 12, 3),
        "goi_cuon": FoodItem("Goi Cuon", 40, 15, "vietnamese", 8, 2),
        "com_tam": FoodItem("Com Tam", 70, 55, "vietnamese", 10, 1),
        "bun_cha": FoodItem("Bun Cha", 45, 30, "vietnamese", 15, 2),
        "ca_phe_sua_da": FoodItem("Ca Phe Sua Da", 50, 25, "vietnamese", 4, 0),
        "che": FoodItem("Che", 60, 35, "vietnamese", 3, 1),
        "banh_xeo": FoodItem("Banh Xeo", 55, 30, "vietnamese", 8, 2),
    },
    "latinx": {
        "arroz_con_pollo": FoodItem("Arroz con Pollo", 60, 45, "latinx", 20, 3),
        "tamales": FoodItem("Tamales", 55, 35, "latinx", 8, 5),
        "ceviche": FoodItem("Ceviche", 0, 5, "latinx", 25, 0),
        "pupusas": FoodItem("Pupusas", 65, 40, "latinx", 10, 4),
        "mole": FoodItem("Mole", 35, 15, "latinx", 12, 4),
        "tres_leches": FoodItem("Tres Leches", 65, 50, "latinx", 6, 0),
        "churros": FoodItem("Churros", 75, 35, "latinx", 3, 1),
        "pozole": FoodItem("Pozole", 45, 25, "latinx", 18, 3),
    }
}

PORTION_MULTIPLIERS = {"1": 0.5, "2": 1.0, "3": 1.5, "4": 2.0}
PROTEIN_REDUCTION = 0.85   # 15% reduction in glycemic impact
FIBER_REDUCTION = 0.90     # 10% reduction in glycemic impact


@dataclass
class MealLog:
    """A single meal log entry from a participant."""
    participant_id: str
    log_date: datetime
    meal_occasion: str
    cuisine: str
    dish: str
    portion_size: str
    protein_added: bool
    fiber_added: bool
    manual_carbs: Optional[float]
    cgm_pre: Optional[float]
    cgm_post: Optional[float]


@dataclass
class GlycemicMetrics:
    """Computed glycemic metrics for a meal."""
    egl: float
    base_carbs: float
    gi: float
    portion_multiplier: float
    modification_factor: float
    glucose_excursion: Optional[float]
    excursion_category: Optional[str]


class GlycemicLoadEngine:
    """
    Auto-calculates estimated glycemic load from meal logs.

    Formula: eGL = (GI / 100) × (carbs × portion × protein_factor × fiber_factor)

    This provides a PREDICTED glucose impact before observing the CGM curve,
    enabling real-time meal recommendations for participants.
    """

    def __init__(self, food_library: Dict = FOOD_LIBRARY):
        self.food_library = food_library

    def calculate_egl(self, meal: MealLog) -> GlycemicMetrics:
        base_carbs = 0.0
        gi = 50.0

        # Look up dish in cultural food library
        if meal.cuisine in self.food_library and meal.dish in self.food_library[meal.cuisine]:
            food_item = self.food_library[meal.cuisine][meal.dish]
            base_carbs = food_item.carbs_per_serving
            gi = food_item.gi
        elif meal.manual_carbs is not None and meal.manual_carbs > 0:
            base_carbs = meal.manual_carbs

        portion_mult = PORTION_MULTIPLIERS.get(meal.portion_size, 1.0)

        # Apply modification factors
        mod_factor = 1.0
        if meal.protein_added:
            mod_factor *= PROTEIN_REDUCTION
        if meal.fiber_added:
            mod_factor *= FIBER_REDUCTION

        egl = round((gi / 100) * (base_carbs * portion_mult * mod_factor), 1)

        # Calculate observed excursion if pre/post CGM available
        excursion = None
        category = None
        if meal.cgm_pre is not None and meal.cgm_post is not None:
            excursion = meal.cgm_post - meal.cgm_pre
            if excursion < 30:
                category = "Minimal"
            elif excursion < 60:
                category = "Moderate"
            else:
                category = "High"

        return GlycemicMetrics(
            egl=egl, base_carbs=base_carbs, gi=gi,
            portion_multiplier=portion_mult, modification_factor=mod_factor,
            glucose_excursion=excursion, excursion_category=category
        )


# ==============================================================================
# P1: Data Quality Validator
# ==============================================================================

class DataQualityValidator:
    """
    Clinical data quality validation aligned with REDCap-native rules.

    Rules:
    1. CGM values outside 50-400 mg/dL are biologically impossible
    2. Future dates are not allowed
    3. Either a dish OR manual carbs must be entered
    4. Excursions >150 mg/dL may indicate data entry errors
    """

    def __init__(self):
        self.rules = [
            {'name': 'cgm_range', 
             'check': lambda r: 50 <= r.get('cgm_pre', 100) <= 400 if pd.notna(r.get('cgm_pre')) else True,
             'severity': 'warning', 'message': 'CGM outside 50-400'},
            {'name': 'future_date', 
             'check': lambda r: pd.to_datetime(r.get('meal_log_date', '2000-01-01')) <= pd.Timestamp.now(),
             'severity': 'error', 'message': 'Future date not allowed'},
            {'name': 'carbs_required', 
             'check': lambda r: pd.notna(r.get('carbs_manual')) or pd.notna(r.get('dish_selected')),
             'severity': 'error', 'message': 'Dish or carbs required'},
            {'name': 'excursion_outlier', 
             'check': lambda r: abs(r.get('glucose_excursion', 0)) < 150 if pd.notna(r.get('glucose_excursion')) else True,
             'severity': 'warning', 'message': 'Excursion >150 mg/dL'},
        ]

    def validate_record(self, record: Dict) -> List[Dict]:
        """Validate a single record against all rules."""
        issues = []
        for rule in self.rules:
            try:
                if not rule['check'](record):
                    issues.append({
                        'rule': rule['name'], 
                        'severity': rule['severity'],
                        'message': rule['message'],
                        'participant_id': record.get('participant_id')
                    })
            except Exception as e:
                issues.append({
                    'rule': rule['name'], 
                    'severity': 'error',
                    'message': f'Validation error: {e}',
                    'participant_id': record.get('participant_id')
                })
        return issues

    def validate_batch(self, df: pd.DataFrame) -> pd.DataFrame:
        """Validate an entire batch of records."""
        all_issues = []
        # Check for duplicates
        dupes = df[df.duplicated(subset=['participant_id', 'meal_log_date', 'meal_occasion'], keep=False)]
        for _, row in dupes.iterrows():
            all_issues.append({
                'rule': 'duplicate_meal', 
                'severity': 'warning',
                'message': 'Duplicate meal log detected',
                'participant_id': row['participant_id']
            })
        # Check each record
        for _, row in df.iterrows():
            all_issues.extend(self.validate_record(row.to_dict()))
        return pd.DataFrame(all_issues)


# ==============================================================================
# P1: Weekly Report Generator
# ==============================================================================

class WeeklyReportGenerator:
    """
    Auto-generates weekly manuscript-ready visualizations.

    Outputs:
    1. Mean glucose excursion by cuisine (with error bars)
    2. Estimated vs. observed glycemic load (validation scatter)
    3. Top-performing dishes (lowest excursion)
    4. Individual time-series (optional)
    """

    def __init__(self, engine: GlycemicLoadEngine):
        self.engine = engine

    def generate(self, df: pd.DataFrame, week_start: datetime, 
                 week_end: datetime, output_dir: str = ".") -> Dict:
        """Generate weekly report with validation."""
        required_cols = ['meal_log_date', 'cuisine_cat', 'glucose_excursion', 
                        'egl', 'cgm_pre', 'cgm_post']
        missing = [c for c in required_cols if c not in df.columns]
        if missing:
            logger.warning(f"Missing columns: {missing}. Available: {list(df.columns)}")
            return {'error': f'Missing required columns: {missing}'}

        df['meal_log_date'] = pd.to_datetime(df['meal_log_date'])
        week_df = df[(df['meal_log_date'] >= week_start) & 
                     (df['meal_log_date'] <= week_end)].copy()

        if len(week_df) == 0:
            return {'error': 'No meals in selected week range'}

        # Cuisine-level summary
        cuisine_summary = week_df.groupby('cuisine_cat').agg({
            'glucose_excursion': ['mean', 'std', 'count'],
            'egl': 'mean', 
            'cgm_pre': 'mean', 
            'cgm_post': 'mean'
        }).reset_index()
        cuisine_summary.columns = ['cuisine_cat', 'mean_excursion', 'sd_excursion', 
                                   'n_meals', 'mean_egl', 'mean_cgm_pre', 'mean_cgm_post']

        # Dish-level summary (minimum 3 observations)
        dish_col = 'dish_selected' if 'dish_selected' in week_df.columns else 'dish'
        dish_summary = week_df.groupby(['cuisine_cat', dish_col]).agg({
            'glucose_excursion': ['mean', 'std', 'count'], 
            'egl': 'mean'
        }).reset_index()
        dish_summary.columns = ['cuisine_cat', 'dish', 'mean_excursion', 
                                'sd_excursion', 'n_meals', 'mean_egl']
        dish_summary = dish_summary[dish_summary['n_meals'] >= 3].sort_values('mean_excursion')

        figs = {}
        cuisine_labels = {1: 'Filipino', 2: 'Indian', 3: 'Vietnamese', 4: 'Latinx'}
        colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4']

        # Plot 1: Mean excursion by cuisine
        fig, ax = plt.subplots(figsize=(10, 6))
        cuisine_summary['cuisine_label'] = cuisine_summary['cuisine_cat'].map(cuisine_labels)
        ax.bar(cuisine_summary['cuisine_label'], cuisine_summary['mean_excursion'],
               yerr=cuisine_summary['sd_excursion']/np.sqrt(cuisine_summary['n_meals']),
               capsize=5, color=colors)
        ax.set_title(f'Mean Glucose Excursion by Cuisine - Week of {week_start.strftime("%Y-%m-%d")}')
        ax.set_ylabel('Glucose Excursion (mg/dL)')
        plt.tight_layout()
        figs['cuisine_excursion'] = fig
        plt.savefig(f"{output_dir}/pb1_cuisine_excursion.png", dpi=150, bbox_inches='tight')
        plt.close()

        # Plot 2: eGL vs observed
        fig, ax = plt.subplots(figsize=(10, 6))
        for cuisine, color in zip([1, 2, 3, 4], colors):
            subset = week_df[week_df['cuisine_cat'] == cuisine]
            ax.scatter(subset['egl'], subset['glucose_excursion'], alpha=0.6, 
                      label=cuisine_labels.get(cuisine), color=color)
        valid = week_df.dropna(subset=['egl', 'glucose_excursion'])
        if len(valid) > 10:
            z = np.polyfit(valid['egl'], valid['glucose_excursion'], 1)
            p = np.poly1d(z)
            ax.plot(valid['egl'].sort_values(), p(valid['egl'].sort_values()), "r--", alpha=0.8)
        ax.set_title('eGL vs. Observed Glucose Excursion')
        ax.set_xlabel('Estimated Glycemic Load')
        ax.set_ylabel('Glucose Excursion (mg/dL)')
        ax.legend()
        plt.tight_layout()
        figs['egl_vs_excursion'] = fig
        plt.savefig(f"{output_dir}/pb1_egl_vs_excursion.png", dpi=150, bbox_inches='tight')
        plt.close()

        return {
            'cuisine_summary': cuisine_summary, 
            'dish_summary': dish_summary,
            'top_performers': dish_summary.head(10), 
            'figures': figs,
            'total_meals': len(week_df), 
            'total_participants': week_df['participant_id'].nunique()
        }


# ==============================================================================
# MAIN
# ==============================================================================

def main():
    """Demo: Process synthetic CGM data and generate weekly report."""
    logger.info("Playbook 1: CGM & Cultural Meal Tracker")
    logger.info("Loading synthetic data...")

    # Load synthetic data
    cgm_df = pd.read_csv('data/sample_cgm_dexcom.csv')
    meals_df = pd.read_csv('data/sample_meal_logs.csv')

    # Process CGM data
    processor = UnifiedCGMProcessor()
    # For demo, we'll use the raw data directly (in production, use processor.process())
    metrics = processor.compute_metrics(cgm_df)
    logger.info(f"CGM Metrics: {json.dumps(metrics, indent=2)}")

    # Validate meal logs
    validator = DataQualityValidator()
    issues = validator.validate_batch(meals_df)
    if len(issues) > 0:
        logger.warning(f"Found {len(issues)} data quality issues")
        print(issues.head())

    # Generate weekly report
    engine = GlycemicLoadEngine()
    reporter = WeeklyReportGenerator(engine)
    week_start = datetime(2026, 1, 1)
    week_end = datetime(2026, 1, 7)

    report = reporter.generate(meals_df, week_start, week_end, output_dir='docs/screenshots')
    logger.info(f"Report generated: {report['total_meals']} meals, {report['total_participants']} participants")

    return report


if __name__ == "__main__":
    main()
