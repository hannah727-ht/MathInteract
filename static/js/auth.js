
import { api, getMe, nextPage, renderHeader } from "/js/common.js";

const page = document.getElementById("site-header").dataset.page;
renderHeader();

for (const link of document.querySelectorAll("a[data-keep-next]")) {
  link.search = location.search;
}

async function submit(form, action) {
  const button = form.querySelector('button[type="submit"]');
  const error = form.querySelector(".form-error");
  const note = form.querySelector(".form-note");
  error.textContent = "";
  if (note) note.textContent = "";
  button.disabled = true;
  try {
    await action();
  } catch (e) {
    error.textContent = e.message;
  } finally {
    button.disabled = false;
  }
}

function checkSame(password, confirm) {
  if (password !== confirm) throw new Error("The two passwords don’t match.");
}

if (page === "login" || page === "signup") {
  getMe().then((me) => { if (me) location.replace(nextPage()); });
}

if (page === "signup") {
  const form = document.getElementById("signup-form");
  form.onsubmit = (event) => {
    event.preventDefault();
    submit(form, async () => {
      const { username, password, password2 } = form.elements;
      checkSame(password.value, password2.value);
      await api("POST", "/api/auth/signup", { username: username.value.trim(), password: password.value });
      location.href = nextPage();
    });
  };
}

if (page === "login") {
  const form = document.getElementById("login-form");
  form.onsubmit = (event) => {
    event.preventDefault();
    submit(form, async () => {
      const { username, password } = form.elements;
      await api("POST", "/api/auth/login", { username: username.value.trim(), password: password.value });
      location.href = nextPage();
    });
  };
}

if (page === "account") {
  const form = document.getElementById("password-form");
  getMe().then((me) => {
    if (!me) location.replace("/login.html?next=/account.html");
    else document.getElementById("account-name").textContent = me.username;
  });
  form.onsubmit = (event) => {
    event.preventDefault();
    submit(form, async () => {
      const { current_password, new_password, new_password2 } = form.elements;
      checkSame(new_password.value, new_password2.value);
      await api("POST", "/api/auth/password", {
        current_password: current_password.value, new_password: new_password.value,
      });
      form.reset();
      form.querySelector(".form-note").textContent = "Your password has been changed.";
    });
  };
}
