// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

async function editCompany(companyId) {
  try {
    const res = await fetch(`/company/get/${companyId}`);
    const result = await res.json();
    if (!result.success) return alert("Failed to fetch company details");

    const company = result.company;
    document.getElementById('editCompanyId').value = company.id;
    document.getElementById('editCompanyName').value = company.name;
    document.getElementById('editCompanyAddress').value = company.address || "";
    openModal('editCompanyModal');
  } catch (err) {
    console.error(err);
    alert("Error fetching company details");
  }
}

document.getElementById('editCompanyForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const formData = new FormData(this);
  const companyId = document.getElementById('editCompanyId').value;

  const submitBtn = this.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';

  try {
    const res = await fetch(`/company/edit/${companyId}`, { method: 'POST', body: formData });
    const result = await res.json();
    if (result.success) {
      location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to save company'));
    }
  } catch (err) {
    console.error(err);
    alert('Failed to save company');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save Changes';
  }
});
