
# ==================== VALIDATION TEMPLATES (STRICT GMP) ====================

class ValidationTemplates:
    """Immutable GMP-compliant templates for validation docs"""
    
    PVP_SECTIONS = [
        "1. Objective", "2. Scope", "3. Responsibility", "4. Validation Approach",
        "5. Reason for Validation", "6. Revalidation Criteria", "7. Product & Batch Details",
        "8. Equipment & Utilities", "9. Raw Material & Packing Material", 
        "10. Process Flow Diagram", "11. Manufacturing Process", "12. Filling & Sealing",
        "13. Visual Inspection", "14. Sampling Plan", "15. Acceptance Criteria",
        "16. Reference Documents", "17. Stability", "18. Deviation Handling",
        "19. Change Control", "20. Abbreviations", "21. Approval"
    ]
    
    PVR_SECTIONS = [
        "1. Objective", "2. Scope", "3. Responsibility", "4. Product & Batch Details",
        "5. Equipment & Machinery List", "6. Raw Material Details", "7. Observations / Results",
        "8. Quality Control Results of Finished Product", "9. Deviation Report",
        "10. Change Control", "11. Conclusion", "12. Summary", "13. Post Approval"
    ]

    @staticmethod
    def get_pvp_objective(product_name):
        return (f"The objective of this protocol is to validate the manufacturing process of {product_name} "
                "to demonstrate that the process operates in a state of control and consistently produces "
                "product meeting predetermined quality attributes and specifications as per cGMP requirements.")

    @staticmethod
    def get_pvr_objective(product_name):
        return (f"The objective of this report is to summarize the data recorded during the process validation "
                f"of {product_name} and to evaluate whether the process consistently meets the "
                "predetermined specifications and quality attributes.")
    
    @staticmethod
    def get_responsibilities():
        return [
            ["Department", "Responsibility"],
            ["Production", "Execution of validation batches, recording of data."],
            ["Quality Assurance", "Review and approval of protocol/report, monitoring of validation."],
            ["Quality Control", "Sampling and testing of validation samples."],
            ["Engineering", "Support for equipment and utilities."]
        ]
    
    @staticmethod
    def get_validation_approach():
        return ("Prospective process validation shall be performed on three consecutive batches. "
                "All critical process parameters and critical quality attributes shall be monitored "
                "and recorded. Any deviation shall be investigated and documented.")
    
    @staticmethod
    def get_revalidation_criteria():
        return [
            ["Criteria", "Description"],
            ["Change in Batch Size", "Change of more than 10% in batch size."],
            ["Change in Equipment", "Change in critical manufacturing equipment."],
            ["Process Change", "Change in critical process parameters."],
            ["Raw Material Change", "Change in vendor or specification of critical raw material."]
        ]

    @staticmethod
    def get_deviation_policy():
        return ("Any deviation observed during the validation execution shall be recorded, investigated, "
                "and closed as per the Standard Operating Procedure for Deviation Handling. "
                "Critical deviations may require re-validation.")

    @staticmethod
    def get_change_control_policy():
        return ("Any change proposed during the validation activity shall be routed through the "
                "Change Control procedure. Impact assessment shall be performed before implementation.")
