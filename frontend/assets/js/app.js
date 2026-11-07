import { ApiError, AuthClient } from "./auth.js";

const auth = new AuthClient();
const page = document.body.dataset.page;

function pageUrl(filename) {
  return new URL(`../../pages/${filename}`, import.meta.url).href;
}

function redirect(filename) {
  window.location.assign(pageUrl(filename));
}

function setMessage(message, kind = "error") {
  const element = document.querySelector("#form-message");
  if (!element) return;
  element.textContent = message;
  element.className = `message ${kind}`;
  element.hidden = false;
}

function setLoading(form, loading, label) {
  const button = form.querySelector("button[type='submit']");
  form.setAttribute("aria-busy", String(loading));
  button.disabled = loading;
  button.textContent = loading ? "Please wait…" : label;
}

function errorMessage(error) {
  return error instanceof ApiError ? error.message : "An unexpected error occurred. Please try again.";
}

function validPassword(password) {
  return password.length >= 8 && password.length <= 128 && /[A-Za-z]/.test(password) && /\d/.test(password);
}

async function redirectIfSessionExists() {
  if (!auth.hasSession()) return;
  try {
    await auth.getCurrentUser();
    redirect("dashboard.html");
  } catch {
    auth.clearSession();
  }
}

async function setupLogin() {
  await redirectIfSessionExists();
  const form = document.querySelector("#login-form");
  if (new URLSearchParams(window.location.search).has("registered")) {
    setMessage("Account created. Please sign in.", "success");
  }
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const identifier = form.identifier.value.trim();
    const password = form.password.value;
    if (!identifier || !password) return setMessage("Enter your username or email and password.");

    setLoading(form, true, "Sign in");
    try {
      await auth.login(identifier, password);
      await auth.getCurrentUser();
      redirect("dashboard.html");
    } catch (error) {
      auth.clearSession();
      setMessage(errorMessage(error));
    } finally {
      setLoading(form, false, "Sign in");
    }
  });
}

async function setupRegister() {
  await redirectIfSessionExists();
  const form = document.querySelector("#register-form");
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    const username = form.username.value.trim();
    const email = form.email.value.trim();
    const password = form.password.value;
    const confirmPassword = form.confirmPassword.value;
    const fullName = form.fullName.value.trim();

    if (!/^[A-Za-z0-9_.-]{3,50}$/.test(username)) return setMessage("Enter a valid username.");
    if (!form.email.checkValidity()) return setMessage("Enter a valid email address.");
    if (!validPassword(password)) return setMessage("Password must be 8–128 characters and include a letter and a number.");
    if (password !== confirmPassword) return setMessage("Password confirmation does not match.");

    setLoading(form, true, "Create account");
    try {
      await auth.register({ username, email, password, full_name: fullName || null });
      window.location.assign(`${pageUrl("login.html")}?registered=1`);
    } catch (error) {
      setMessage(errorMessage(error));
    } finally {
      setLoading(form, false, "Create account");
    }
  });
}

async function setupDashboard() {
  try {
    const user = await auth.getCurrentUser();
    const displayName = user.full_name || user.username;
    document.querySelector("#user-name").textContent = displayName;
    document.querySelector("#welcome-name").textContent = displayName;
    document.querySelector("#user-details").textContent = `${user.email} · ${user.role}`;
  } catch {
    auth.clearSession();
    redirect("login.html");
    return;
  }

  document.querySelector("#logout-button").addEventListener("click", async () => {
    const button = document.querySelector("#logout-button");
    button.disabled = true;
    try {
      await auth.logout();
    } catch {
      // Local credentials are always cleared by AuthClient.logout.
    }
    redirect("login.html");
  });
}

if (page === "login") setupLogin();
if (page === "register") setupRegister();
if (page === "dashboard") setupDashboard();
