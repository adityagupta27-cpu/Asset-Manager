let editingEmployeeId = null;
let employeeList = [];

async function loadEmployees() {
    const search = document.getElementById("employeeSearch").value.trim();
    try {
        employeeList = await apiFetch(`/employees?search=${encodeURIComponent(search)}`);
        const rows = employeeList.map((employee) => `
            <tr class="border-b border-zinc-100">
                <td class="px-4 py-3">${employee.id}</td>
                <td class="px-4 py-3">${escapeHtml(employee.name)}</td>
                <td class="px-4 py-3">${escapeHtml(employee.email)}</td>
                <td class="px-4 py-3">${escapeHtml(employee.department)}</td>
                <td class="px-4 py-3 ${isAdmin() ? "" : "hidden"}">
                    <button class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-50" onclick="editEmployee(${employee.id})">Edit</button>
                    <button class="ml-2 rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50" onclick="deleteEmployee(${employee.id})">Delete</button>
                </td>
            </tr>
        `).join("");

        document.getElementById("employeeTable").innerHTML = rows || `
            <tr>
                <td colspan="5" class="px-4 py-8 text-center text-zinc-500">No employees found</td>
            </tr>
        `;
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function saveEmployee(event) {
    event.preventDefault();

    const employee = {
        name: document.getElementById("name").value.trim(),
        email: document.getElementById("email").value.trim(),
        department: document.getElementById("department").value.trim()
    };

    const path = editingEmployeeId ? `/employees/${editingEmployeeId}` : "/employees";
    const method = editingEmployeeId ? "PUT" : "POST";

    try {
        const wasEditing = Boolean(editingEmployeeId);
        await apiFetch(path, {
            method,
            body: JSON.stringify(employee)
        });
        resetForm();
        showAlert(wasEditing ? "Employee updated" : "Employee added");
        await loadEmployees();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

function editEmployee(id) {
    const employee = employeeList.find((item) => item.id === id);
    if (!employee) {
        return;
    }
    editingEmployeeId = employee.id;
    document.getElementById("name").value = employee.name;
    document.getElementById("email").value = employee.email;
    document.getElementById("department").value = employee.department;
    document.getElementById("formTitle").textContent = "Edit Employee";
    document.getElementById("submitEmployee").textContent = "Update Employee";
    document.getElementById("cancelEdit").classList.remove("hidden");
}

function resetForm() {
    editingEmployeeId = null;
    document.getElementById("employeeForm").reset();
    document.getElementById("formTitle").textContent = "Add Employee";
    document.getElementById("submitEmployee").textContent = "Add Employee";
    document.getElementById("cancelEdit").classList.add("hidden");
}

async function deleteEmployee(id) {
    if (!confirm("Delete this employee?")) {
        return;
    }

    try {
        await apiFetch(`/employees/${id}`, { method: "DELETE" });
        showAlert("Employee deleted");
        await loadEmployees();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

requireLogin();
setupShell();
document.getElementById("employeeForm").addEventListener("submit", saveEmployee);
document.getElementById("employeeSearch").addEventListener("input", loadEmployees);
document.getElementById("cancelEdit").addEventListener("click", resetForm);
loadEmployees();
