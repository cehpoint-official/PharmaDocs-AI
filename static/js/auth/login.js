// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import { getAuth, signInWithEmailAndPassword, signInWithPopup, GoogleAuthProvider } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js';

// Firebase configuration
const firebaseConfig = {
    apiKey: "{{ firebase_api_key }}",
    authDomain: "{{ firebase_project_id }}.firebaseapp.com",
    projectId: "{{ firebase_project_id }}",
    storageBucket: "{{ firebase_project_id }}.appspot.com",
    appId: "{{ firebase_app_id }}"
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const provider = new GoogleAuthProvider();

// Show/hide password
document.getElementById('togglePassword').addEventListener('click', function() {
    const password = document.getElementById('password');
    const icon = this.querySelector('i');

    if (password.type === 'password') {
        password.type = 'text';
        icon.classList.replace('fa-eye', 'fa-eye-slash');
    } else {
        password.type = 'password';
        icon.classList.replace('fa-eye-slash', 'fa-eye');
    }
});

// Handle form submission
document.getElementById('loginForm').addEventListener('submit', async function(e) {
    e.preventDefault();

    const email = document.getElementById('email').value;
    const password = document.getElementById('password').value;
    const loginBtn = document.getElementById('loginBtn');
    const errorDiv = document.getElementById('loginError');
    const errorMessage = document.getElementById('errorMessage');

    // Loading state
    loginBtn.disabled = true;
    loginBtn.innerHTML = '<i class="fas fa-spinner fa-spin mr-2"></i>Logging in...';
    errorDiv.classList.add('hidden');

    try {
        const userCredential = await signInWithEmailAndPassword(auth, email, password);
        const user = userCredential.user;
        const idToken = await user.getIdToken();

        const response = await fetch('/auth/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idToken })
        });

        const result = await response.json();
        if (result.success) {
            window.location.href = '/dashboard/';
        } else {
            throw new Error(result.error || 'Login failed');
        }
    } catch (error) {
        errorMessage.textContent = error.message || 'Login failed. Please try again.';
        errorDiv.classList.remove('hidden');
    } finally {
        loginBtn.disabled = false;
        loginBtn.innerHTML = '<i class="fas fa-sign-in-alt mr-2"></i>Login';
    }
});

// Google login
document.getElementById('googleLogin').addEventListener('click', async () => {
    const errorDiv = document.getElementById('loginError');
    const errorMessage = document.getElementById('errorMessage');

    try {
        const result = await signInWithPopup(auth, provider);
        const user = result.user;
        const idToken = await user.getIdToken();

        const response = await fetch('/auth/verify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ idToken })
        });

        const backendResult = await response.json();
        if (backendResult.success) {
            window.location.href = '/dashboard/';
        } else {
            throw new Error(backendResult.error || 'Login failed');
        }
    } catch (error) {
        errorMessage.textContent = 'Google login failed. Please try again.';
        errorDiv.classList.remove('hidden');
    }
});
