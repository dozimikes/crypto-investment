document.addEventListener('DOMContentLoaded', () => {
    const depositForm = document.getElementById('deposit-form');
    const responseMessage = document.getElementById('response-message');

    depositForm.addEventListener('submit', (event) => {
        event.preventDefault(); // Prevent form submission

        const depositType = document.getElementById('deposit-type').value;
        const amount = document.getElementById('amount').value;
        const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;

        // Validate input
        if (!depositType || !amount || amount <= 0) {
            responseMessage.innerHTML = `<div class="alert alert-danger">Please provide valid deposit details.</div>`;
            return;
        }

        // Make a POST request to the backend
        fetch('/deposit/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': csrfToken, // Include CSRF token
            },
            body: JSON.stringify({ deposit_type: depositType, amount: amount }),
        })
            .then((response) => response.json())
            .then((data) => {
                if (data.error) {
                    responseMessage.innerHTML = `<div class="alert alert-danger">${data.error}</div>`;
                } else {
                    if (depositType === 'crypto') {
                        responseMessage.innerHTML = `
                            <div class="alert alert-success">
                                Crypto Deposit Address: <strong>${data.crypto_address}</strong><br>
                                Amount: ${data.amount}
                            </div>`;
                    } else if (depositType === 'fiat') {
                        responseMessage.innerHTML = `
                            <div class="alert alert-success">
                                ${data.message}<br>
                                Amount: ${data.amount}
                            </div>`;
                    }
                }
            })
            .catch((error) => {
                responseMessage.innerHTML = `<div class="alert alert-danger">An error occurred. Please try again later.</div>`;
                console.error('Error:', error);
            });
    });
});
