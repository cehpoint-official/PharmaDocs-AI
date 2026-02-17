// Copyright (C) 2025 Soumyadeep Ghosh <soumyadeepghosh2004@zohomail.in>
// All Rights Reserved.

// Global variables for Stripe
let stripe = null;
let elements = null;
let cardElement = null;

document.addEventListener('DOMContentLoaded', function () {
    const subscriptionModal = document.getElementById('subscriptionModal');
    if (!subscriptionModal) return;

    const closeModal = subscriptionModal.querySelector('.close');
    const planCards = subscriptionModal.querySelectorAll('.plan-card');

    // Initialize Stripe if publishable key is available
    if (window.STRIPE_PUBLISHABLE_KEY) {
        initializeStripe();
    }

    // Function to show the modal
    function showModal() {
        subscriptionModal.style.display = 'flex';
        loadUpgradePopupData();
    }

    // Function to hide the modal
    function hideModal() {
        subscriptionModal.style.display = 'none';
        if (cardElement) {
            cardElement.unmount();
        }
    }

    // Close modal when close button is clicked
    if (closeModal) {
        closeModal.onclick = hideModal;
    }

    // Close modal when clicking outside of it
    window.onclick = function (event) {
        if (event.target == subscriptionModal) {
            hideModal();
        }
    };

    // Handle plan selection
    planCards.forEach(card => {
        card.addEventListener('click', function () {
            const plan = this.dataset.plan;
            const currentPlan = getCurrentUserPlan();
            
            if (plan === currentPlan) {
                alert('You are already on this plan!');
                return;
            }
            
            subscribeToPlan(plan);
        });
    });

    // Function to initialize Stripe
    function initializeStripe() {
        try {
            stripe = Stripe(window.STRIPE_PUBLISHABLE_KEY);
            elements = stripe.elements();
        } catch (error) {
            console.error('Error initializing Stripe:', error);
        }
    }

    // Function to get current user plan
    function getCurrentUserPlan() {
        // This will be populated by the server-side template
        return window.USER_SUBSCRIPTION_PLAN || 'free';
    }

    // Function to load upgrade popup data
    function loadUpgradePopupData() {
        fetch('/subscription/upgrade-popup-data')
            .then(response => response.json())
            .then(data => {
                if (data.success) {
                    updateSubscriptionModal(data);
                }
            })
            .catch(error => {
                console.error('Error loading upgrade popup data:', error);
            });
    }

    // Function to update subscription modal with data
    function updateSubscriptionModal(data) {
        const modalContent = subscriptionModal.querySelector('.modal-content');
        if (modalContent && data.plans) {
            // Update modal content with plan information
            // This would be implemented based on your modal structure
        }
    }

    // Enhanced function to subscribe to a plan
    function subscribeToPlan(plan) {
        if (plan === 'free') {
            // Handle free plan downgrade
            if (confirm('Are you sure you want to downgrade to the free plan? You will lose access to premium features.')) {
                fetch('/user/subscribe', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ plan: plan }),
                })
                .then(response => response.json())
                .then(data => {
                    if (data.success) {
                        alert(data.message);
                        hideModal();
                        setTimeout(() => window.location.reload(), 1000);
                    } else {
                        alert('Error: ' + data.error);
                    }
                })
                .catch(error => {
                    console.error('Subscription error:', error);
                    alert('An error occurred while subscribing. Please try again.');
                });
            }
        } else {
            // Handle paid plan upgrade - redirect to proper payment flow
            window.location.href = '/subscription/plans';
        }
    }

    // Enhanced subscription management functions
    window.subscribeToPlan = subscribeToPlan;
    window.showModal = showModal;
    window.hideModal = hideModal;

    const upgradePlanLink = document.getElementById('upgradePlanLink');
    if (upgradePlanLink) {
        upgradePlanLink.addEventListener('click', function (e) {
            e.preventDefault();
            showModal();
        });
    }

    const upgradePlanNav = document.getElementById('upgradePlanNav');
    if (upgradePlanNav) {
        upgradePlanNav.addEventListener('click', function (e) {
            e.preventDefault();
            showModal();
        });
    }


    const manageSubscriptionBtn = document.getElementById('manageSubscriptionBtn');
    if (manageSubscriptionBtn) {
        manageSubscriptionBtn.addEventListener('click', function (e) {
            e.preventDefault();
            window.location.href = '/user/profile';
        });
    }







    // Check user status on page load
    function checkUserStatus() {
        fetch('/user/status')
            .then(response => response.json())
            .then(data => {
                if (data.success && data.show_subscription_popup) {
                    showModal();
                }
            })
            .catch(error => {
                console.error('Error fetching user status:', error);
            });
    }

    
});
