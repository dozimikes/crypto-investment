interface DepositData {
  deposit_type: string;
  amount: number;
  currency?: string;
}

const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]') as HTMLInputElement;
const depositForm = document.getElementById('deposit-form') as HTMLFormElement;
const depositTypeSelect = document.getElementById('deposit_type') as HTMLSelectElement;
const amountInput = document.getElementById('amount') as HTMLInputElement;
const cryptoDepositSection = document.getElementById('crypto-deposit-section') as HTMLElement;
const fiatDepositSection = document.getElementById('fiat_deposit') as HTMLElement;
const cryptoDepositButton = document.getElementById('crypto-deposit-btn') as HTMLElement;
const paymentResultDiv = document.getElementById('payment-result') as HTMLElement;

depositTypeSelect.addEventListener('change', function () {
  const depositType = depositTypeSelect.value;
  if (depositType === 'fiat') {
    fiatDepositSection.style.display = 'block';
    cryptoDepositSection.style.display = 'none';
  } else if (depositType === 'crypto') {
    fiatDepositSection.style.display = 'none';
    cryptoDepositSection.style.display = 'block';
  }
});

cryptoDepositButton.addEventListener('click', function () {
  const amount = parseFloat(amountInput.value);
  if (isNaN(amount) || amount <= 0) {
    paymentResultDiv.textContent = 'Invalid amount. Please enter a valid number greater than 0.';
    return;
  }

  const depositData: DepositData = {
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
    .then(response => {
      if (!response.ok) {
        throw new Error('Server responded with a non-OK status');
      }
      return response.json();
    })
    .then(data => {
      if (data.crypto_address) {
        paymentResultDiv.innerHTML = `
          <p>Send ${data.amount} USD worth of cryptocurrency to:</p>
          <p><strong>${data.crypto_address}</strong></p>`;
      } else if (data.error) {
        paymentResultDiv.textContent = data.error;
      }
    })
    .catch(error => {
      paymentResultDiv.textContent = `An error occurred: ${error.message}`;
    });
});

// Submit the form for normal deposits (without crypto generation)
depositForm.addEventListener('submit', function (e: Event) {
  e.preventDefault();
  const depositData: DepositData = {
    deposit_type: depositTypeSelect.value,
    amount: parseFloat(amountInput.value),
    currency: depositTypeSelect.value === 'fiat' ? (document.getElementById('currency') as HTMLSelectElement).value : undefined,
  };

  if (isNaN(depositData.amount) || depositData.amount <= 0) {
    paymentResultDiv.textContent = 'Invalid amount. Please enter a valid number greater than 0.';
    return;
  }

  fetch('/deposit/', {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'X-CSRFToken': csrfToken.value,
    },
    body: JSON.stringify(depositData),
  })
    .then(response => {
      if (!response.ok) {
        throw new Error('Server responded with a non-OK status');
      }
      return response.json();
    })
    .then(data => {
      if (data.message) {
        paymentResultDiv.textContent = data.message;
      } else if (data.error) {
        paymentResultDiv.textContent = data.error;
      }
    })
    .catch(error => {
      paymentResultDiv.textContent = `An error occurred: ${error.message}`;
    });
});
