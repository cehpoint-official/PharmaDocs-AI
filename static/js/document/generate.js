// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

document.addEventListener("DOMContentLoaded", () => {
  const generationModal = new bootstrap.Modal(document.getElementById("generationModal"));

  // Generate Document
  const generateBtns = document.querySelectorAll("#generateDocumentBtn, #generateDocumentBtnAlt");
  generateBtns.forEach(btn => {
    btn.addEventListener("click", async () => {
      const documentId = btn.getAttribute("data-document-id");
      generationModal.show();

      try {
        const response = await fetch(`/documents/${documentId}/generate`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({})
        });

        const result = await response.json();

        if (result.success) {
          window.location.reload();
        } else {
          generationModal.hide();
          alert("Error: " + (result.error || "Failed to generate document"));
        }
      } catch (error) {
        generationModal.hide();
        console.error("Error:", error);
        alert("Failed to generate document");
      }
    });
  });

  // Edit Document
  const editBtn = document.getElementById("editDocumentBtn");
  if (editBtn) {
    editBtn.addEventListener("click", () => {
      const documentId = editBtn.getAttribute("data-document-id");
      window.location.href = `/documents/create?edit=${documentId}`;
    });
  }

  // Delete Document
  const deleteBtn = document.getElementById("deleteDocumentBtn");
  if (deleteBtn) {
    deleteBtn.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to delete this document? This action cannot be undone.")) {
        return;
      }

      const documentId = deleteBtn.getAttribute("data-document-id");

      try {
        const response = await fetch(`/documents/${documentId}/delete`, {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });

        const result = await response.json();

        if (result.success) {
          window.location.href = "/documents";
        } else {
          alert("Error: " + (result.error || "Failed to delete document"));
        }
      } catch (error) {
        console.error("Error:", error);
        alert("Failed to delete document");
      }
    });
  }
});
