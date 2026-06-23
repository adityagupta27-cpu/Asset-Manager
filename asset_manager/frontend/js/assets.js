let editingAssetId = null;
let assetList = [];

async function loadAssets() {
    const search = document.getElementById("assetSearch").value.trim();
    try {
        assetList = await apiFetch(`/assets?search=${encodeURIComponent(search)}`);
        const rows = assetList.map((asset) => `
            <tr class="border-b border-zinc-100">
                <td class="px-4 py-3">${asset.id}</td>
                <td class="px-4 py-3">${escapeHtml(asset.asset_name)}</td>
                <td class="px-4 py-3">${escapeHtml(asset.asset_type)}</td>
                <td class="px-4 py-3">${escapeHtml(asset.serial_number)}</td>
                <td class="px-4 py-3">${statusBadge(asset.status)}</td>
                <td class="px-4 py-3 ${isAdmin() ? "" : "hidden"}">
                    <button class="rounded-md border border-zinc-300 px-3 py-1.5 text-sm hover:bg-zinc-50" onclick="editAsset(${asset.id})">Edit</button>
                    <button class="ml-2 rounded-md border border-red-200 px-3 py-1.5 text-sm text-red-700 hover:bg-red-50" onclick="deleteAsset(${asset.id})">Delete</button>
                </td>
            </tr>
        `).join("");

        document.getElementById("assetTable").innerHTML = rows || `
            <tr>
                <td colspan="6" class="px-4 py-8 text-center text-zinc-500">No assets found</td>
            </tr>
        `;
    } catch (error) {
        showAlert(error.message, "error");
    }
}

async function saveAsset(event) {
    event.preventDefault();

    const asset = {
        asset_name: document.getElementById("assetName").value.trim(),
        asset_type: document.getElementById("assetType").value.trim(),
        serial_number: document.getElementById("serialNumber").value.trim(),
        status: document.getElementById("status").value
    };

    const path = editingAssetId ? `/assets/${editingAssetId}` : "/assets";
    const method = editingAssetId ? "PUT" : "POST";

    try {
        const wasEditing = Boolean(editingAssetId);
        await apiFetch(path, {
            method,
            body: JSON.stringify(asset)
        });
        resetForm();
        showAlert(wasEditing ? "Asset updated" : "Asset added");
        await loadAssets();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

function editAsset(id) {
    const asset = assetList.find((item) => item.id === id);
    if (!asset) {
        return;
    }

    editingAssetId = asset.id;
    document.getElementById("assetName").value = asset.asset_name;
    document.getElementById("assetType").value = asset.asset_type;
    document.getElementById("serialNumber").value = asset.serial_number;
    document.getElementById("status").value = asset.status;
    document.getElementById("formTitle").textContent = "Edit Asset";
    document.getElementById("submitAsset").textContent = "Update Asset";
    document.getElementById("cancelEdit").classList.remove("hidden");
}

function resetForm() {
    editingAssetId = null;
    document.getElementById("assetForm").reset();
    document.getElementById("formTitle").textContent = "Add Asset";
    document.getElementById("submitAsset").textContent = "Add Asset";
    document.getElementById("cancelEdit").classList.add("hidden");
}

async function deleteAsset(id) {
    if (!confirm("Delete this asset?")) {
        return;
    }

    try {
        await apiFetch(`/assets/${id}`, { method: "DELETE" });
        showAlert("Asset deleted");
        await loadAssets();
    } catch (error) {
        showAlert(error.message, "error");
    }
}

requireLogin();
setupShell();
document.getElementById("assetForm").addEventListener("submit", saveAsset);
document.getElementById("assetSearch").addEventListener("input", loadAssets);
document.getElementById("cancelEdit").addEventListener("click", resetForm);
loadAssets();
