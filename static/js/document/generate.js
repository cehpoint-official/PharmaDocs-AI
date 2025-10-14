// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

document.addEventListener("DOMContentLoaded", () => {
  const generationModal = document.getElementById("generationModal");

  // Helper functions for modal
  function showModal() {
    generationModal.classList.remove("hidden");
  }

  function hideModal() {
    generationModal.classList.add("hidden");
  }

  // Generate Document
  const generateBtns = document.querySelectorAll("#generateDocumentBtn, #generateDocumentBtnAlt");
  
  generateBtns.forEach(btn => {
    btn.addEventListener("click", async (e) => {
      e.preventDefault();
      const documentId = btn.getAttribute("data-document-id");
      
      if (!documentId) {
        alert("Error: Document ID not found");
        return;
      }
      
      showModal();

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
          hideModal();
          alert("Error: " + (result.error || "Failed to generate document"));
        }
      } catch (error) {
        hideModal();
        console.error("Error:", error);
        alert("Failed to generate document: " + error.message);
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

  // Cleanup Files
  const cleanupBtn = document.getElementById("cleanupFilesBtn");
  if (cleanupBtn) {
    cleanupBtn.addEventListener("click", async () => {
      if (!confirm("Are you sure you want to cleanup uploaded files? This will delete STP files, raw data files, and method analysis files from storage. This action cannot be undone.")) {
        return;
      }

      const documentId = cleanupBtn.getAttribute("data-document-id");

      try {
        const response = await fetch(`/documents/${documentId}/cleanup-files`, {
          method: "POST",
          headers: { "Content-Type": "application/json" }
        });

        const result = await response.json();

        if (result.success) {
          alert("Files cleaned up successfully!");
          window.location.reload();
        } else {
          alert("Error: " + (result.error || "Failed to cleanup files"));
        }
      } catch (error) {
        console.error("Error:", error);
        alert("Failed to cleanup files");
      }
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
