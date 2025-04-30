/* General body styles */
body {
    font-family: 'Arial', sans-serif;
    margin: 0;
    padding: 0;
    height: 100vh;
    background-color: #f0f0f0; /* Default light background */
    display: flex;
    justify-content: center;
    align-items: center;
    transition: background-color 0.3s ease, color 0.3s ease;
}

/* Dark Mode Styles */
body.dark-mode {
    background-color: #121212;
    color: white;
}

/* Login and Register page background */
.login-container, .register-container {
    width: 100%;
    height: 100%;
    background: url('../static/BACKGROUND IMAGE.png') no-repeat center center fixed;
    background-size: cover;
    display: flex;
    justify-content: center;
    align-items: center;
}

/* Container to center the login form */
.form-container {
    background-color: rgba(255, 255, 255, 0.8); /* Slightly transparent white */
    padding: 40px;
    border-radius: 15px; /* Rounded corners */
    width: 300px;
    text-align: center;
    box-shadow: 0 5px 30px rgba(0, 0, 0, 0.1); /* Shadow effect */
    color: black; /* Ensure text color remains visible in light mode */
}

/* Dark Mode Form Container */
body.dark-mode .form-container {
    background-color: rgba(255, 255, 255, 0.2); /* Slightly darker background for dark mode */
    color: white; /* Text color changes to white in dark mode */
}

/* Title styling */
h2 {
    color: #FF6347;
    font-size: 30px;
    margin-bottom: 20px;
}

/* Dark Mode Title Styling */
body.dark-mode h2 {
    color: #FF6347;
}

/* Button styling */
button {
    width: 100%;
    padding: 12px;
    background-color: #FF6347;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s ease;
}

/* Dark Mode Button */
body.dark-mode button {
    background-color: #FF4500;
}

/* Button hover effect */
button:hover {
    background-color: #FF4500;
}

/* Link to switch between login/register */
p {
    margin-top: 20px;
    color: #FF6347;
}

a {
    text-decoration: none;
    color: #FF4500;
    font-weight: bold;
}

/* Error message styles */
.error {
    color: red;
    font-size: 14px;
}

/* Responsive design for small screens */
@media (max-width: 500px) {
    .form-container {
        width: 90%;
        padding: 30px;
    }
}

/* Dashboard Container */
.dashboard-container {
    width: 100%;
    height: 100%;
    display: flex;
    justify-content: center;
    align-items: center;
    background-color: #f0f0f0; /* Light background for logged-in page */
    transition: background-color 0.3s ease;
}

/* Dark Mode Dashboard Container */
body.dark-mode .dashboard-container {
    background-color: #121212; /* Dark background */
}

/* Dashboard Form Container */
.form-container.dashboard-form {
    background-color: rgba(255, 255, 255, 0.8); /* Transparent white background */
    padding: 40px;
    border-radius: 15px;
    width: 350px;
    text-align: center;
    box-shadow: 0 5px 30px rgba(0, 0, 0, 0.1); /* Shadow effect */
}

/* Dark Mode Dashboard Form */
body.dark-mode .form-container.dashboard-form {
    background-color: rgba(255, 255, 255, 0.2); /* Darker background for dark mode */
    color: white;
}

/* Dashboard Header */
h2 {
    color: #FF6347;
    font-size: 30px;
    margin-bottom: 20px;
}

/* Dashboard Button Container */
.button-container {
    margin-top: 20px;
}

/* Dashboard Button */
button {
    width: 100%;
    padding: 12px;
    background-color: #FF6347;
    color: white;
    border: none;
    border-radius: 10px;
    font-size: 16px;
    cursor: pointer;
    transition: background-color 0.3s ease;
    margin-bottom: 15px; /* Add space between buttons */
}

/* Dark Mode Dashboard Button */
body.dark-mode .dashboard-form button {
    background-color: #FF4500;
}

/* Dashboard Button Hover */
button:hover {
    background-color: #FF4500;
}

/* Logout Link */
.logout-link {
    color: #FF6347;
    text-decoration: none;
    font-weight: bold;
    margin-top: 20px;
    display: block;
}

/* Dark Mode Logout Link */
body.dark-mode .logout-link {
    color: #FF6347;
}

/* Dark Mode Toggle Switch */
.toggle-container {
    position: fixed;
    top: 20px;
    right: 20px;
    display: flex;
    align-items: center;
}

.switch {
    position: relative;
    display: inline-block;
    width: 60px;
    height: 34px;
}

.switch input {
    opacity: 0;
    width: 0;
    height: 0;
}

.slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: #ccc;
    transition: 0.4s;
    border-radius: 50px;
}

.slider:before {
    position: absolute;
    content: "";
    height: 26px;
    width: 26px;
    border-radius: 50px;
    left: 4px;
    bottom: 4px;
    background-color: white;
    transition: 0.4s;
}

input:checked + .slider {
    background-color: #FF6347;
}

input:checked + .slider:before {
    transform: translateX(26px);
}

/* Stars and Moon/Sun Inside the Toggle */
.slider:after {
    content: "🌙";
    position: absolute;
    right: 12px;
    top: 8px;
    font-size: 14px;
}

input:checked + .slider:before {
    background-color: yellow;
    content: "🌞";
    position: absolute;
    left: 12px;
    top: 8px;
    font-size: 14px;
}