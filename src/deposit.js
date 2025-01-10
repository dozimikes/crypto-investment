"use strict";
const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]');
const depositForm = document.getElementById('deposit-form');
const depositTypeSelect = document.getElementById('deposit_type');
const amountInput = document.getElementById('amount');
const cryptoDepositSection = document.getElementById('crypto-deposit-section');
const fiatDepositSection = document.getElementById('fiat_deposit');
const cryptoDepositButton = document.getElementById('crypto-deposit-btn');
const paymentResultDiv = document.getElementById('payment-result');
depositTypeSelect.addEventListener('change', function () {
    const depositType = depositTypeSelect.value;
    if (depositType === 'fiat') {
        fiatDepositSection.style.display = 'block';
        cryptoDepositSection.style.display = 'none';
    }
    else if (depositType === 'crypto') {
        fiatDepositSection.style.display = 'none';
        cryptoDepositSection.style.display = 'block';
    }
});
cryptoDepositButton.addEventListener('click', function () {
    const amount = parseFloat(amountInput.value);
    if (!amount || amount <= 0) {
        paymentResultDiv.textContent = 'Invalid amount.';
        return;
    }
    const depositData = {
        deposit_type: 'crypto',
        amount: amount,
    };
    fetch('/deposit/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken.value,
        },
        body: JSON.stringify(depositData),
    })
        .then(response => response.json())
        .then(data => {
        if (data.crypto_address) {
            paymentResultDiv.innerHTML = `
          <p>Send ${data.amount} USD worth of cryptocurrency to:</p>
          <p><strong>${data.crypto_address}</strong></p>`;
        }
        else if (data.error) {
            paymentResultDiv.textContent = data.error;
        }
    })
        .catch(error => {
        paymentResultDiv.textContent = `An error occurred: ${error.message}`;
    });
});
// Submit the form for normal deposits (without crypto generation)
depositForm.addEventListener('submit', function (e) {
    e.preventDefault();
    const depositData = {
        deposit_type: depositTypeSelect.value,
        amount: parseFloat(amountInput.value),
        currency: depositTypeSelect.value === 'fiat' ? document.getElementById('currency').value : undefined,
    };
    fetch('/deposit/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': csrfToken.value,
        },
        body: JSON.stringify(depositData),
    })
        .then(response => response.json())
        .then(data => {
        if (data.message) {
            paymentResultDiv.textContent = data.message;
        }
        else if (data.error) {
            paymentResultDiv.textContent = data.error;
        }
    })
        .catch(error => {
        paymentResultDiv.textContent = `An error occurred: ${error.message}`;
    });
});

document.addEventListener('DOMContentLoaded', function () {
    const depositTypeSelect = document.getElementById('deposit_type');
    const fiatDepositSection = document.getElementById('fiat_deposit');
    const cryptoDepositSection = document.getElementById('crypto-deposit-section');

    // Toggle fiat/crypto sections based on deposit type
    depositTypeSelect.addEventListener('change', function () {
        if (depositTypeSelect.value === 'fiat') {
            fiatDepositSection.style.display = 'block';
            cryptoDepositSection.style.display = 'none';
        } else if (depositTypeSelect.value === 'crypto') {
            fiatDepositSection.style.display = 'none';
            cryptoDepositSection.style.display = 'block';
        }
    });

    // Trigger change event on load to set the correct initial state
    depositTypeSelect.dispatchEvent(new Event('change'));
});

