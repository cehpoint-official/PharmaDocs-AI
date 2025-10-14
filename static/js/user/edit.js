// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

document.getElementById('editProfileForm').addEventListener('submit', async function(e) {
  e.preventDefault();
  const formData = new FormData(this);
  const submitBtn = this.querySelector('button[type="submit"]');
  submitBtn.disabled = true;
  submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Saving...';

  try {
    const res = await fetch('/user/edit', { method: 'POST', body: formData });
    const result = await res.json();
    if (result.success) {
      alert('Profile updated successfully');
      closeModal('editProfileModal');
      location.reload();
    } else {
      alert('Error: ' + (result.error || 'Failed to update profile'));
    }
  } catch (err) {
    console.error(err);
    alert('Failed to update profile');
  } finally {
    submitBtn.disabled = false;
    submitBtn.innerHTML = '<i class="fas fa-save mr-2"></i>Save';
  }
});
