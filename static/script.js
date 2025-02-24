document.addEventListener("DOMContentLoaded", function () {
    const authorizeButton = document.getElementById("authorize-button");
    const dashboardDiv = document.getElementById("dashboard");

    // Ensure the dashboardDiv exists
    if (!dashboardDiv) {
        console.error("Dashboard div not found!");
        return;
    }

    // Add click event to the authorize button
    if (authorizeButton) {
        authorizeButton.addEventListener("click", function () {
            window.location.href = "/authorize";
        });
    }

    // Fetch dashboard data
    fetch("/dashboard")
        .then(response => {
            if (!response.ok) {
                throw new Error("Network response was not OK");
            }
            return response.json();
        })
        .then(data => {
            // Check if fitness_data and health_analysis exist
            if (data.fitness_data && data.health_analysis) {
                displayHealthData(data);
            } else {
                dashboardDiv.innerHTML = "<p>Please authorize access to view your health data.</p>";
            }
        })
        .catch(error => {
            console.error("Error fetching dashboard data:", error);
            dashboardDiv.innerHTML = "<p>Error loading data. Please try again.</p>";
        });
});

function displayHealthData(data) {
    const dashboardDiv = document.getElementById("dashboard");

    // Ensure dashboardDiv exists
    if (!dashboardDiv) {
        console.error("Dashboard div not found!");
        return;
    }

    // Generate step count table
    let stepCounts = data.fitness_data.map(day => {
        // Ensure day.date is a valid date
        const date = new Date(day.date);
        const formattedDate = isNaN(date.getTime()) ? "Invalid Date" : date.toLocaleDateString();
        return `
            <tr>
                <td>${formattedDate}</td>
                <td>${day.steps}</td>
            </tr>
        `;
    }).join("");

    // Generate health recommendations
    let recommendations = data.health_analysis.recommendations.map(rec => `
        <li><strong>${rec.category}:</strong> ${rec.suggestion}
            <ul>
                ${rec.action_items.map(item => `<li>${item}</li>`).join("")}
            </ul>
        </li>
    `).join("");

    // Update the dashboard content
    dashboardDiv.innerHTML = `
        <h3>Health Analysis</h3>
        <p><strong>Risk Score:</strong> ${data.health_analysis.risk_score}</p>

        <h4>Recommendations:</h4>
        <ul>
            ${recommendations}
        </ul>

        <h4>Step Count Over Time</h4>
        <table border="1">
            <thead>
                <tr>
                    <th>Date</th>
                    <th>Steps</th>
                </tr>
            </thead>
            <tbody>
                ${stepCounts}
            </tbody>
        </table>
    `;
}