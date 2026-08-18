class ExplanationBuilder:
    """
    Assembles feature contribution lists and classification outputs 
    into plain-text human-friendly explanation narratives.
    """
    @classmethod
    def generate_human_explanation(cls, predicted_grade: str, top_positive: list, top_negative: list) -> str:
        """
        Builds a readable narrative summary from classifications and normalized attributions.
        """
        grade = str(predicted_grade).strip().upper()
        
        if grade in ["EXCELLENT", "GOOD"]:
            title = f"Overall Data Quality is predicted as {grade.title()}.\n\n"
            summary = "The record displays high indicators of completeness, validity, and uniqueness. "
            
            # Highlight positive attributes
            highlights = []
            for item in top_positive[:3]:
                feat_name = item["feature"].replace("_", " ").title()
                pct = item["percentage"]
                highlights.append(f"• {feat_name} (+{pct}%)")
                
            if highlights:
                summary += "Key contributing factors include:\n" + "\n".join(highlights)
            else:
                summary += "All data quality dimensions meet high enterprise standards."
                
            return title + summary
            
        else: # AVERAGE, POOR
            title = f"Overall Data Quality is predicted as {grade.title()}.\n\n"
            summary = "The record flags significant quality issues that reduce its grade. "
            
            # Highlight negative attributes (which are lowering the quality score)
            warnings = []
            for item in top_negative[:3]:
                feat_name = item["feature"].replace("_", " ").title()
                pct = item["percentage"]
                warnings.append(f"• {feat_name} (-{pct}%)")
                
            if warnings:
                summary += "The primary quality degradation factors are:\n" + "\n".join(warnings)
            else:
                # If there are no negative attribution vectors, list positive features that were weak
                weaknesses = []
                for item in top_positive[-3:]:
                    feat_name = item["feature"].replace("_", " ").title()
                    weaknesses.append(f"• Low {feat_name}")
                if weaknesses:
                    summary += "Primary factors relate to weak dimension scores:\n" + "\n".join(weaknesses)
                else:
                    summary += "Review recommended due to low overall dimensions score."
                    
            return title + summary
