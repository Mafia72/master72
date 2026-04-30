const accordionItems = document.querySelectorAll(".accordion-item");

accordionItems.forEach((item) => {
  const trigger = item.querySelector(".accordion-trigger");

  trigger.addEventListener("click", () => {
    const isOpen = item.classList.contains("is-open");

    accordionItems.forEach((otherItem) => {
      otherItem.classList.remove("is-open");
      otherItem.querySelector(".accordion-trigger").setAttribute("aria-expanded", "false");
    });

    if (!isOpen) {
      item.classList.add("is-open");
      trigger.setAttribute("aria-expanded", "true");
    }
  });
});

const observer = new IntersectionObserver(
  (entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("is-visible");
      }
    });
  },
  { threshold: 0.14 }
);

document.querySelectorAll(".reveal").forEach((element) => observer.observe(element));

const leadForm = document.querySelector(".lead-form");
const leadSection = document.querySelector(".lead");
const leadSuccess = document.querySelector(".lead-success");
const leadPhoneInput = leadForm?.querySelector('input[name="phone"]');
const localSpamWindowMs = 60_000;

const formatPhone = (value) => {
  const digits = value.replace(/\D/g, "").replace(/^8/, "7").slice(0, 11);
  const normalized = digits.startsWith("7") ? digits : `7${digits}`.slice(0, 11);
  const country = normalized.slice(0, 1);
  const part1 = normalized.slice(1, 4);
  const part2 = normalized.slice(4, 7);
  const part3 = normalized.slice(7, 9);
  const part4 = normalized.slice(9, 11);

  let result = `+${country}`;
  if (part1) {
    result += ` (${part1}`;
  }
  if (part1.length === 3) {
    result += ")";
  }
  if (part2) {
    result += ` ${part2}`;
  }
  if (part3) {
    result += `-${part3}`;
  }
  if (part4) {
    result += `-${part4}`;
  }

  return result;
};

const getPhoneDigits = (value) => value.replace(/\D/g, "").replace(/^8/, "7");

leadPhoneInput?.addEventListener("input", () => {
  leadPhoneInput.value = formatPhone(leadPhoneInput.value);
});

leadPhoneInput?.addEventListener("focus", () => {
  if (!leadPhoneInput.value.trim()) {
    leadPhoneInput.value = "+7";
  }
});

const setStatus = (element, message, state) => {
  element.textContent = message;
  element.dataset.state = state || "";
};

const showSuccessState = () => {
  if (!leadSection || !leadSuccess) {
    return;
  }

  leadSection.classList.add("is-success");
  leadSuccess.classList.add("is-visible");
  leadSuccess.setAttribute("aria-hidden", "false");

  window.setTimeout(() => {
    leadSection.classList.remove("is-success");
    leadSuccess.classList.remove("is-visible");
    leadSuccess.setAttribute("aria-hidden", "true");
  }, 4200);
};

leadForm?.addEventListener("submit", async (event) => {
  event.preventDefault();

  const form = event.currentTarget;
  const button = form.querySelector(".button--primary");
  const status = form.querySelector(".lead-form__status");
  const phoneInput = form.querySelector('input[name="phone"]');
  const messageInput = form.querySelector('textarea[name="message"]');
  const trapInput = form.querySelector('input[name="company"]');

  if (!button || !status || !phoneInput || !messageInput || !trapInput) {
    return;
  }

  const phone = phoneInput.value.trim();
  const message = messageInput.value.trim();
  const phoneDigits = getPhoneDigits(phone);
  const lastSubmittedAt = Number(window.localStorage.getItem("leadLastSubmittedAt") || "0");

  if (!phone || phoneDigits.length !== 11) {
    setStatus(status, "Введите корректный номер телефона.", "error");
    phoneInput.focus();
    return;
  }

  if (trapInput.value.trim()) {
    setStatus(status, "Не удалось отправить заявку.", "error");
    return;
  }

  if (Date.now() - lastSubmittedAt < localSpamWindowMs) {
    setStatus(status, "Заявка уже отправлялась недавно. Попробуйте через минуту.", "error");
    return;
  }

  const originalText = button.textContent;
  button.disabled = true;
  button.textContent = "Отправляем...";
  setStatus(status, "", "");

  try {
    const response = await fetch("/api/lead", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ phone, message, company: trapInput.value.trim() }),
    });

    const payload = await response.json();

    if (!response.ok || !payload.ok) {
      throw new Error(payload.message || "Не удалось отправить заявку.");
    }

    window.localStorage.setItem("leadLastSubmittedAt", String(Date.now()));
    setStatus(status, payload.message, "success");
    form.reset();
    phoneInput.value = "";
    showSuccessState();
  } catch (error) {
    setStatus(status, error.message || "Ошибка отправки. Попробуйте ещё раз.", "error");
  } finally {
    button.disabled = false;
    button.textContent = originalText;
  }
});
