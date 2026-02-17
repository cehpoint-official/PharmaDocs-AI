// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved

// Authentication utilities
class AuthManager {
    constructor() {
        this.init();
    }

    init() {
        // Bind form handlers if they exist
        this.bindLoginForm();
        this.bindRegisterForm();
        this.bindPasswordToggles();
        this.bindGoogleAuth();
    }

    bindLoginForm() {
        const loginForm = document.getElementById('loginForm');
        if (!loginForm) return;

        loginForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleLogin(loginForm);
        });
    }

    bindRegisterForm() {
        const registerForm = document.getElementById('registerForm');
        if (!registerForm) return;

        registerForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            await this.handleRegister(registerForm);
        });
    }

    bindPasswordToggles() {
        // Toggle password visibility
        document.querySelectorAll('[id^="togglePassword"]').forEach(button => {
            button.addEventListener('click', () => {
                const targetId = button.id.replace('toggle', '').toLowerCase();
                const passwordField = document.getElementById(targetId) ||
                                    document.getElementById(targetId.replace('password', 'Password'));

                if (passwordField) {
                    const icon = button.querySelector('i');

                    if (passwordField.type === 'password') {
                        passwordField.type = 'text';
                        icon.classList.remove('fa-eye');
                        icon.classList.add('fa-eye-slash');
                    } else {
                        passwordField.type = 'password';
                        icon.classList.remove('fa-eye-slash');
                        icon.classList.add('fa-eye');
                    }
                }
            });
        });
    }

    bindGoogleAuth() {
        // Google login/register buttons
        document.querySelectorAll('[id$="googleLogin"], [id$="googleRegister"]').forEach(button => {
            button.addEventListener('click', () => {
                this.handleGoogleAuth();
            });
        });
    }

    async handleLogin(form) {
        const email = form.querySelector('#email').value;
        const password = form.querySelector('#password').value;
        const submitBtn = form.querySelector('button[type="submit"]');

        this.setLoadingState(submitBtn, 'Logging in...');
        this.hideError();

        try {
            // Sign in with Firebase
            const userCredential = await window.firebaseModules.signInWithEmailAndPassword(
                window.firebaseAuth, email, password
            );

            await window.firebaseUtils.handleAuthSuccess(userCredential.user);

        } catch (error) {
            console.error('Login error:', error);
            this.showError(this.getErrorMessage(error));
        } finally {
            this.resetLoadingState(submitBtn, 'Login');
        }
    }

    async handleRegister(form) {
        const formData = new FormData(form);
        const name = formData.get('name');
        const email = formData.get('email');
        const password = formData.get('password');
        const confirmPassword = formData.get('confirmPassword');
        const submitBtn = form.querySelector('button[type="submit"]');

        // Validate form
        if (!this.validatePassword(password)) {
            this.showError('Password must be at least 8 characters with uppercase, lowercase, and number.');
            return;
        }

        if (password !== confirmPassword) {
            this.showError('Passwords do not match.');
            return;
        }

        this.setLoadingState(submitBtn, 'Creating Account...');
        this.hideError();

        try {
            // Create user with Firebase
            const userCredential = await window.firebaseModules.createUserWithEmailAndPassword(
                window.firebaseAuth, email, password
            );

            // Update user profile with name
            await window.firebaseModules.updateProfile(userCredential.user, {
                displayName: name
            });

            await window.firebaseUtils.handleAuthSuccess(userCredential.user);

        } catch (error) {
            console.error('Registration error:', error);
            this.showError(this.getErrorMessage(error));
        } finally {
            this.resetLoadingState(submitBtn, 'Create Account');
        }
    }

    async handleGoogleAuth() {
        try {
            await window.firebaseModules.signInWithRedirect(
                window.firebaseAuth,
                window.googleProvider
            );
        } catch (error) {
            console.error('Google auth error:', error);
            this.showError('Google authentication failed. Please try again.');
        }
    }

    validatePassword(password) {
        if (!password || password.length < 8) return false;

        const hasUpper = /[A-Z]/.test(password);
        const hasLower = /[a-z]/.test(password);
        const hasNumber = /\d/.test(password);

        return hasUpper && hasLower && hasNumber;
    }

    getErrorMessage(error) {
        switch (error.code) {
            case 'auth/email-already-in-use':
                return 'Email address is already in use.';
            case 'auth/weak-password':
                return 'Password is too weak.';
            case 'auth/invalid-email':
                return 'Invalid email address.';
            case 'auth/user-not-found':
                return 'No account found with this email address.';
            case 'auth/wrong-password':
                return 'Incorrect password.';
            case 'auth/too-many-requests':
                return 'Too many failed attempts. Please try again later.';
            default:
                return error.message || 'Authentication failed. Please try again.';
        }
    }

    showError(message) {
        const errorDiv = document.getElementById('authError') ||
                        document.getElementById('loginError') ||
                        document.getElementById('registerError');
        const errorMessage = document.getElementById('errorMessage');

        if (errorDiv && errorMessage) {
            errorMessage.textContent = message;
            errorDiv.classList.remove('d-none');
        }
    }

    hideError() {
        const errorDiv = document.getElementById('authError') ||
                        document.getElementById('loginError') ||
                        document.getElementById('registerError');

        if (errorDiv) {
            errorDiv.classList.add('d-none');
        }
    }

    setLoadingState(button, text) {
        button.disabled = true;
        button.innerHTML = `<i class="fas fa-spinner fa-spin me-2"></i>${text}`;
    }

    resetLoadingState(button, text) {
        button.disabled = false;
        button.innerHTML = `<i class="fas fa-sign-in-alt me-2"></i>${text}`;
    }

    async logout() {
        try {
            await window.firebaseModules.signOut(window.firebaseAuth);
            window.location.href = '/logout';
        } catch (error) {
            console.error('Logout error:', error);
        }
    }
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    window.authManager = new AuthManager();
});

// Export for global use
window.AuthManager = AuthManager;
