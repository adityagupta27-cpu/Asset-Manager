requireLogin();
setupShell();

const session = getSession();
document.getElementById("profileUsername").textContent = session.username;
document.getElementById("profileRole").textContent = session.role;
