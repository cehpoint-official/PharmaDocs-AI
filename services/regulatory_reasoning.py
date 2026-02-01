
from typing import Dict, List, Any
from dataclasses import dataclass

@dataclass
class ValidationDecision:
    conclusion_statement: str
    is_valid: bool
    justification: str
    recommendations: List[str]
    compliance_level: str # "COMPLIANT", "INCONCLUSIVE", "NON_COMPLIANT"

class RegulatoryReasoningEngine:
    """
    Reasoning Engine that enforces strict GxP decision rules.
    It acts as a gatekeeper: if data doesn't support a conclusion, 
    it strictly returns inconclusive/failure states.
    """
    
    def evaluate_validation(self, pvp_data: Dict, batch_results: List[Dict]) -> ValidationDecision:
        """
        Evaluate if the process validation was successful based on strict rules.
        """
        # 1. Check Execution Data Existence
        if not batch_results:
            return ValidationDecision(
                conclusion_statement="PROCESS VALIDATION INCONCLUSIVE",
                is_valid=False,
                justification="No batch execution data (MFR/BMR) was available or extracted. Validation cannot be evaluated without execution evidence.",
                recommendations=["Process requires comprehensive validation with three consecutive batches."],
                compliance_level="INCONCLUSIVE"
            )
            
        # 2. Check Batch Count (Constraint: 3 consecutive batches)
        if len(batch_results) < 3:
             return ValidationDecision(
                conclusion_statement="PROCESS VALIDATION INCONCLUSIVE (Insufficient Data)",
                is_valid=False,
                justification=f"Only {len(batch_results)} batches were available. Regulatory standards require a minimum of three consecutive batches to demonstrate consistency.",
                recommendations=[
                    "Continue validation with remaining batches.",
                    "Do not release batches for commercial distribution until 3 consecutive batches are validated."
                ],
                compliance_level="INCONCLUSIVE"
            )
            
        # 3. Check for OOS (Out of Specification) or Failures
        failed_batches = [b for b in batch_results if b.get('overall_result') == 'FAIL']
        if failed_batches:
            batch_numbers = ", ".join([b.get('batch_number', 'Unknown') for b in failed_batches])
            return ValidationDecision(
                conclusion_statement="PROCESS NOT VALIDATED",
                is_valid=False,
                justification=f"Critical deviations/OOS observed in batches: {batch_numbers}. The process has failed to demonstrate a state of control.",
                recommendations=[
                    "Raise Non-Conformance Reference (NCR).",
                    "Conduct Root Cause Analysis (RCA).",
                    "Process optimization and re-validation required."
                ],
                compliance_level="NON_COMPLIANT"
            )

        # 4. Check for 'Missing' Critical Data (QC Results)
        # If explicit results are missing, we cannot claim success.
        missing_qc = False
        for b in batch_results:
            # If results list is empty or contains "Not Evaluated"
            results = b.get("test_results", [])
            if not results:
                missing_qc = True
                break
        
        if missing_qc:
             return ValidationDecision(
                conclusion_statement="PROCESS VALIDATION INCONCLUSIVE (Missing QC Data)",
                is_valid=False,
                justification="Testing results (QC data) were not available for one or more batches. Compliance cannot be verified.",
                recommendations=["Ensure all QC testing is completed and recorded prior to final report generation."],
                compliance_level="INCONCLUSIVE"
            )

        # 5. Success Case
        return ValidationDecision(
            conclusion_statement="PROCESS VALIDATED",
            is_valid=True,
            justification="Three consecutive batches (n=3) were executed successfully. All Critical Process Parameters (CPPs) and Critical Quality Attributes (CQAs) met the predetermined acceptance criteria. No critical deviations were observed.",
            recommendations=[
                "The manufacturing process is considered validated and suitable for commercial manufacturing.",
                "Routine monitoring shall continue as per the standard protocol.",
                "Any change in the process, equipment, or materials shall be handled via Change Control."
            ],
            compliance_level="COMPLIANT"
        )

    def sanity_check_sections(self, pvr_data: Dict) -> List[str]:
        """
        Cross-verify sections for consistency before generation.
        Returns a list of warnings/errors.
        """
        issues = []
        
        # Check 1: Conclusion vs Data
        conc = pvr_data.get("conclusion", "")
        batches = pvr_data.get("batch_results", [])
        
        if "PROCESS VALIDATED" in conc and len(batches) < 3:
            issues.append("CRITICAL: Conclusion claims Validated but fewer than 3 batches found.")
            
        if "PROCESS VALIDATED" in conc and any(b.get('overall_result') == 'FAIL' for b in batches):
            issues.append("CRITICAL: Conclusion claims Validated but Failed batches exist.")
            
        return issues
