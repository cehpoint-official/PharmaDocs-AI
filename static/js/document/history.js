// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

let documentToDelete = null;

function deleteDocument(documentId) {
  documentToDelete = documentId;
  document.getElementById("deleteModal").classList.remove("hidden");
}

function closeDeleteModal() {
  document.getElementById("deleteModal").classList.add("hidden");
  documentToDelete = null;
}

document.addEventListener("DOMContentLoaded", () => {
  const confirmBtn = document.getElementById("confirmDeleteBtn");

  confirmBtn.addEventListener("click", async function () {
    if (!documentToDelete) return;

    const btn = this;
    btn.disabled = true;
    btn.innerHTML = '<i class="fas fa-spinner fa-spin mr-1"></i> Deleting...';

    try {
      const response = await fetch(`/documents/${documentToDelete}/delete`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
      });

      const result = await response.json();

      if (result.success) {
        location.reload();
      } else {
        alert("Error: " + (result.error || "Failed to delete document"));
      }
    } catch (error) {
      console.error("Error:", error);
      alert("Failed to delete document");
    } finally {
      btn.disabled = false;
      btn.innerHTML = '<i class="fas fa-trash mr-1"></i> Delete';
      closeDeleteModal();
    }
  });
});
