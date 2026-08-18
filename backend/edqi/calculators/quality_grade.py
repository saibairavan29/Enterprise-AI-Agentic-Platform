import logging

logger = logging.getLogger(__name__)

class QualityGradeCalculator:
    """
    Translates numeric overall score to letter grades (e.g. A+, A, B, C, D, F)
    based on configuration.
    """
    @classmethod
    def calculate_grade(cls, score: float, rules: dict) -> str:
        """
        Calculates quality letter grade from score using boundary ranges configurations.
        """
        boundaries = rules.get("grade_boundaries", {
            "A+": [95.0, 100.0],
            "A": [90.0, 94.99],
            "B": [80.0, 89.99],
            "C": [70.0, 79.99],
            "D": [60.0, 69.99],
            "F": [0.0, 59.99]
        })

        for grade, bounds in boundaries.items():
            if len(bounds) == 2:
                lower = float(bounds[0])
                upper = float(bounds[1])
                # Inclusive check of score range
                if lower <= score <= upper:
                    return grade

        # Fallbacks
        if score >= 90.0:
            return "A"
        elif score >= 80.0:
            return "B"
        elif score >= 70.0:
            return "C"
        elif score >= 60.0:
            return "D"
        else:
            return "F"
