async function loadFormOptions() {
    if (!isAdmin()) {
        return;
    }

    const [employees, assets] = await Promise.all([
        apiFetch("/employees"),
        apiFetch("/assets")
    ]);

    document.getElementById("employeeId").innerHTML = employees.map((employee) => `
        <option value="${employee.id}">${escapeHtml(employee.name)} - ${escapeHtml(employee.department)}</option>
    `).join("");

    const availableAssets = assets.filter((asset) => asset.status === "Available");
    document.getElementById("assetId").innerHTML = availableAssets.map((asset) => `
        <option value="${asset.id}">${escapeHtml(asset.asset_name)} - ${escapeHtml(asset.serial_number)}</option>
    `).join("");
}

async function loadAssignments() {
    try {
        const assignments = await apiFetch("/assignments");
        const rows = assignments.map((assignment) => {
            const active = !assignment.returned_date;
            return `
                <tr class="border-b border-zinc-100">
                    <td class="px-4 py-3">${assignment.id}</td>
                    <td class="px-4 py-3">${escapeHtml(assignment.employee_name)}</td>
                    <td class="px-4 py-3">${escapeHtml(assignment.asset_name)}</td>
                    <td class="px-4 py-3">${escapeHtml(assignment.serial_number)}</td>
                    <td class="px-4 py-3">${escapeHtml(assignment.assigned_date)}</td>
                    <td class="px-4 py-3">${assignment.returned_date ? escapeHtml(assignment.returned_date) : statusBadge("Assigned")}</td>
                    <td class="px-4 py-3 ${isAdmin() ? "" : "hidden"}">
                        ${active ? `<button class="rounded-md border border-emerald-200 px-3 py-1.5 text-sm text-emerald-700 hover:bg-emerald-50" onclick="returnAsset(${assignment.id})">Return</button>` : ""}
                    </td>
                </tr>
            `;
        }).join("");

        document.getElementById("assignmentTable").innerHTML = rows || `
            <tr>
                <td colspan="7" class="px-4 py-8 text-center text-zinc-500">No assignments found</td>
            </tr>
        `;
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function assignAsset(event) {
    event.preventDefault();

    const employeeId = document.getElementById("employeeId").value;
    const assetId = document.getElementById("assetId").value;

    if (!employeeId || !assetId) {
        showAlert("Please select an employee and an available asset", "error");
        return;
    }

    try {
        await apiFetch("/assignments", {
            method: "POST",
            body: JSON.stringify({
                employee_id: Number(employeeId),
                asset_id: Number(assetId)
            })
        });
        showAlert("Asset assigned");
        await loadFormOptions();
        await loadAssignments();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function returnAsset(id) {
    if (!confirm("Return this asset?")) {
        return;
    }

    try {
        await apiFetch(`/assignments/${id}/return`, { method: "PUT" });
        showAlert("Asset returned");
        await loadFormOptions();
        await loadAssignments();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

requireLogin();
setupShell();
if (isAdmin()) {
    document.getElementById("assignmentForm").addEventListener("submit", assignAsset);
    loadFormOptions().catch((error) => showAlert(error.message, "error"));
}
loadAssignments();
