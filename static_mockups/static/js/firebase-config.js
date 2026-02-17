// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

// Firebase Configuration and Initialization
const firebaseConfig = {
    // These will be injected by the server
    apiKey: window.FIREBASE_API_KEY,
    authDomain: `${window.FIREBASE_PROJECT_ID}.firebaseapp.com`,
    projectId: window.FIREBASE_PROJECT_ID,
    storageBucket: `${window.FIREBASE_PROJECT_ID}.appspot.com`,
    appId: window.FIREBASE_APP_ID
};

// Initialize Firebase
import { initializeApp } from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-app.js';
import {
    getAuth,
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signInWithRedirect,
    getRedirectResult,
    GoogleAuthProvider,
    updateProfile,
    signOut
} from 'https://www.gstatic.com/firebasejs/10.7.1/firebase-auth.js';

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const googleProvider = new GoogleAuthProvider();

// Export for use in other modules
window.firebaseAuth = auth;
window.googleProvider = googleProvider;
window.firebaseModules = {
    signInWithEmailAndPassword,
    createUserWithEmailAndPassword,
    signInWithRedirect,
    getRedirectResult,
    GoogleAuthProvider,
    updateProfile,
    signOut
};

// Auto-handle redirect results
getRedirectResult(auth).then(async (result) => {
    if (result) {
        console.log('Redirect result received:', result.user.email);
        await handleAuthSuccess(result.user);
    }
}).catch((error) => {
    console.error('Redirect result error:', error);
    showAuthError(error.message);
});

// Handle successful authentication
async function handleAuthSuccess(user) {
    try {
        // Get ID token
        const idToken = await user.getIdToken();

        // Send to backend for verification
        const response = await fetch('/auth/verify', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ idToken: idToken })
        });

        const result = await response.json();

        if (result.success) {
            // Redirect to dashboard
            window.location.href = '/dashboard/';
        } else {
            throw new Error(result.error || 'Authentication failed');
        }
    } catch (error) {
        console.error('Auth success handler error:', error);
        showAuthError(error.message);
    }
}

// Show authentication error
function showAuthError(message) {
    // Find error display elements
    const errorDiv = document.getElementById('authError') || document.getElementById('loginError') || document.getElementById('registerError');
    const errorMessage = document.getElementById('errorMessage');

    if (errorDiv && errorMessage) {
        errorMessage.textContent = message;
        errorDiv.classList.remove('d-none');
    } else {
        // Fallback to alert
        alert('Authentication Error: ' + message);
    }
}

// Export utility functions
window.firebaseUtils = {
    handleAuthSuccess,
    showAuthError
};

// Firebase Auth state change listener
auth.onAuthStateChanged((user) => {
    if (user) {
        console.log('User is signed in:', user.email);
        // Update UI to show authenticated state
        document.body.classList.add('authenticated');
    } else {
        console.log('User is signed out');
        // Update UI to show unauthenticated state
        document.body.classList.remove('authenticated');
    }
});
