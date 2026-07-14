document.getElementById("year").textContent = new Date().getFullYear();

const form = document.getElementById("contactForm");
const statusEl = document.getElementById("formStatus");
const btn = document.getElementById("submitBtn");

// Where the contact endpoint lives. Same-origin /api by default; override if hosted separately.
const CONTACT_ENDPOINT = window.CONTACT_ENDPOINT || "/api/contact";

form.addEventListener("submit", async (e) => {
  e.preventDefault();
  statusEl.className = "form-status";
  statusEl.textContent = "";

  const data = Object.fromEntries(new FormData(form).entries());
  if (!data.name || !data.email || !data.message) {
    statusEl.classList.add("err");
    statusEl.textContent = "Please fill in your name, email, and message.";
    return;
  }
  const emailOk = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(data.email);
  if (!emailOk) {
    statusEl.classList.add("err");
    statusEl.textContent = "Please enter a valid email address.";
    return;
  }

  btn.disabled = true;
  const original = btn.textContent;
  btn.textContent = "Sending…";
  try {
    const res = await fetch(CONTACT_ENDPOINT, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!res.ok) throw new Error((await res.json().catch(() => ({}))).detail || "Send failed");
    statusEl.classList.add("ok");
    statusEl.textContent = "Thanks — your message is on its way. We'll be in touch shortly.";
    form.reset();
  } catch (err) {
    statusEl.classList.add("err");
    statusEl.textContent =
      "We couldn't send that just now. Please email us directly at agi@science.delivery.";
  } finally {
    btn.disabled = false;
    btn.textContent = original;
  }
});
