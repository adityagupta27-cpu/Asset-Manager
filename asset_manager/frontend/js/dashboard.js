async function loadDashboard() {
    try {
        const data = await apiFetch("/dashboard");
        const stats = data.stats;

        document.getElementById("totalEmployees").textContent = stats.total_employees;
        document.getElementById("totalAssets").textContent = stats.total_assets;
        document.getElementById("assignedAssets").textContent = stats.assigned_assets;
        document.getElementById("availableAssets").textContent = stats.available_assets;

        const rows = data.recent_assignments.map((item) => `
            <tr class="border-b border-zinc-100">
                <td class="px-4 py-3">${escapeHtml(item.employee_name)}</td>
                <td class="px-4 py-3">${escapeHtml(item.asset_name)}</td>
                <td class="px-4 py-3">${escapeHtml(item.assigned_date)}</td>
                <td class="px-4 py-3">${item.returned_date ? escapeHtml(item.returned_date) : statusBadge("Assigned")}</td>
            </tr>
        `).join("");

        document.getElementById("recentAssignments").innerHTML = rows || `
            <tr>
                <td colspan="4" class="px-4 py-8 text-center text-zinc-500">No assignments yet</td>
            </tr>
        `;
    } catch (error) {
        showAlert(error.message, "error");
    }
}

requireLogin();
setupShell();
loadDashboard();
