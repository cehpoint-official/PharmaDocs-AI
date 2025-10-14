// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

document.addEventListener("DOMContentLoaded", function() {
            const docTypes = document.querySelectorAll("input[name='document_type']");
            const paramSections = {
                "AMV": "amvParameters",
                "PV": "pvParameters",
                "Stability": "stabilityParameters",
                "Degradation": "degradationParameters",
                "Compatibility": "compatibilityParameters"
            };
            const container = document.getElementById("documentParameters");

            function updateParameters() {
                container.innerHTML = "";
                const selected = document.querySelector("input[name='document_type']:checked").value;
                if (paramSections[selected]) {
                    const template = document.getElementById(paramSections[selected]);
                    if (template) {
                        container.innerHTML = template.innerHTML;
                    }
                }
            }

            docTypes.forEach(radio => {
                radio.addEventListener("change", updateParameters);
            });

            // initialize on load
            updateParameters();
        });
