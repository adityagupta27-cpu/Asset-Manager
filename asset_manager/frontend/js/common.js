const API_URL = "http://127.0.0.1:8010";

function getSession() {
    return {
        token: localStorage.getItem("token"),
        username: localStorage.getItem("username"),
        role: localStorage.getItem("role")
    };
}

function requireLogin() {
    if (!getSession().token) {
        window.location.href = "login.html";
    }
}

function isAdmin() {
    return getSession().role === "Admin";
}

function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("username");
    localStorage.removeItem("role");
    window.location.href = "login.html";
}

async function apiFetch(path, options = {}) {
    const session = getSession();
    const headers = {
        "Content-Type": "application/json",
        ...(options.headers || {})
    };

    if (session.token) {
        headers.Authorization = `Bearer ${session.token}`;
    }

    const response = await fetch(`${API_URL}${path}`, {
        ...options,
        headers
    });

    if (response.status === 401) {
        logout();
        return;
    }

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.detail || "Something went wrong");
    }

    return data;
}

function setupShell() {
    const session = getSession();
    const profileLabel = document.getElementById("profileLabel");
    const roleLabel = document.getElementById("roleLabel");

    if (profileLabel) {
        profileLabel.textContent = session.username || "Guest";
    }

    if (roleLabel) {
        roleLabel.textContent = session.role || "";
    }

    document.querySelectorAll("[data-admin-only]").forEach((element) => {
        element.classList.toggle("hidden", !isAdmin());
    });
}

function showAlert(message, type = "success") {
    const alertBox = document.getElementById("alertBox");
    if (!alertBox) {
        alert(message);
        return;
    }

    const colors = type === "error"
        ? "border-red-200 bg-red-50 text-red-700"
        : "border-emerald-200 bg-emerald-50 text-emerald-700";

    alertBox.className = `mb-4 rounded-md border px-4 py-3 text-sm ${colors}`;
    alertBox.textContent = message;
    alertBox.classList.remove("hidden");

    setTimeout(() => alertBox.classList.add("hidden"), 3500);
}

function escapeHtml(value) {
    return String(value ?? "")
        .replaceAll("&", "&amp;")
        .replaceAll("<", "&lt;")
        .replaceAll(">", "&gt;")
        .replaceAll('"', "&quot;")
        .replaceAll("'", "&#039;");
}

function statusBadge(status) {
    const styles = {
        Available: "bg-emerald-100 text-emerald-700",
        Assigned: "bg-sky-100 text-sky-700",
        Maintenance: "bg-amber-100 text-amber-700",
        Retired: "bg-zinc-200 text-zinc-700"
    };

    return `<span class="rounded-full px-2 py-1 text-xs font-medium ${styles[status] || styles.Retired}">${escapeHtml(status)}</span>`;
}
