function showMessage(type, text) {
    const messageBox = document.getElementById('response-message');
    messageBox.classList.add(type);
    messageBox.textContent = text;

    setTimeout(() => {
        messageBox.classList.remove('success', 'error');
    }, 5000);
}

document.getElementById("create-ticket-form").addEventListener("submit", async function(event) {
    event.preventDefault();

   // Collect form data
   const name = document.getElementById("name").value;
   const email = document.getElementById("email").value;
   const count = parseInt(document.getElementById("count").value);
   const seat_type = document.getElementById("seat_type").value;

   const payload = { name, email, count, seat_type };

   // Call the API
   try {
    const response = await fetch("/api/create_ticket", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify(payload)
        });

        const result = await response.json();

        // Display success or error messages
        if (response.ok) {
            showMessage('success', result.message || 'Ticket(s) has been created successfully!');
            document.getElementById("create-ticket-form").reset();
            document.getElementById("name").focus();
        } else {
            showMessage('error', result.error || 'An unknown error occurred.');
        }
    } catch (error) {
        showMessage('error', error || 'An unknown error occurred.');
    }
});

// Function to load seat types from the API and populate the dropdown
async function loadSeatTypes() {
    try {
        const response = await fetch("/api/seat_types");
        const data = await response.json();

        if (response.ok && Array.isArray(data.seat_types)) {
            const select = document.getElementById("seat_type");

            // Clear existing options
            select.innerHTML = "";

            // Populate options
            data.seat_types.forEach((type, index) => {
                const option = document.createElement("option");
                option.value = type;
                option.textContent = type;

                // Select the first option by default
                if (index === 0) {
                    option.selected = true;
                }

                select.appendChild(option);
            });
        } else {
            showMessage("error", "Failed to load seat types.");
        }
    } catch (error) {
        console.error("Error while loading seat types:", error);
        showMessage("error", "An error occurred while loading seat types.");
    }
}

// Run this function after the DOM is fully loaded
document.addEventListener("DOMContentLoaded", () => {
    loadSeatTypes();
});
