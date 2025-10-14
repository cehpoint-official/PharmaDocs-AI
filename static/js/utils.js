// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

// Utility to open and close modals
function openModal(id) {
  document.getElementById(id).classList.remove('hidden');
  document.getElementById(id).classList.add('flex');
}
function closeModal(id) {
  document.getElementById(id).classList.remove('flex');
  document.getElementById(id).classList.add('hidden');
}

// Toggle dropdown menu
function toggleDropdown(btn) {
  const menu = btn.nextElementSibling;
  menu.classList.toggle('hidden');
}

