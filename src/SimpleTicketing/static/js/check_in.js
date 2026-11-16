let isLocked = false;
let isMobileDevice = /Mobi|Android/i.test(navigator.userAgent);
let config = isMobileDevice ? { fps: 10, qrbox: 250 } : { fps: 10, qrbox: 300 };

function onScanSuccess(qrCodeMessage) {
    if (isLocked) return;

    isLocked = true;

    fetch('/api/check_in_ticket', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ ticket_code: qrCodeMessage })
    })
    .then(async response => {
        const resultDiv = document.getElementById('result');
        const validTicketSound = document.getElementById('valid-ticket-sound');
        const invalidTicketSound = document.getElementById('invalid-ticket-sound');
        const formContainer = document.querySelector('.form-container');

        const data = await response.json();  // always JSON
        formContainer.classList.remove('success', 'error');

        if (response.ok) {
            formContainer.classList.add('success');
            resultDiv.innerText = data.message || "Valid ticket!";
            validTicketSound.play();
            if (navigator.vibrate) navigator.vibrate(200);
        } else {
            formContainer.classList.add('error');
            resultDiv.innerText = data.error || "Invalid or already used ticket!";
            invalidTicketSound.play();
            if (navigator.vibrate) navigator.vibrate([100, 50, 100]);
        }

        // Reset background color after timeout
        setTimeout(() => {
            formContainer.classList.remove('success', 'error');
        }, 2000);
    })
    .catch(error => {
        console.error('Error sending request:', error);
        const resultDiv = document.getElementById('result');
        const formContainer = document.querySelector('.form-container');
        formContainer.classList.add('error');
        resultDiv.innerText = "Connection error!";

        setTimeout(() => {
            formContainer.classList.remove('error');
        }, 5000);
    })
    .finally(() => {
        // Unlock after x seconds
        setTimeout(() => {
            isLocked = false;
        }, 2000);
    });
}

let html5QrcodeScanner = new Html5QrcodeScanner("qr-reader", config);
html5QrcodeScanner.render(onScanSuccess);
