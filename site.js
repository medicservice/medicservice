/* MEDIC SERVICE — shared interactions */
(function () {
  "use strict";

  /* ---- sticky header shadow ---- */
  const header = document.querySelector(".site-header");
  if (header) {
    const onScroll = () => header.classList.toggle("scrolled", window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
  }

  /* ---- mobile drawer ---- */
  const drawer = document.querySelector(".drawer");
  document.querySelectorAll("[data-open-drawer]").forEach((b) =>
    b.addEventListener("click", () => drawer && drawer.classList.add("open")));
  document.querySelectorAll("[data-close-drawer]").forEach((b) =>
    b.addEventListener("click", () => drawer && drawer.classList.remove("open")));
  if (drawer) drawer.querySelector(".drawer__scrim")?.addEventListener("click", () => drawer.classList.remove("open"));

  /* ---- FAQ accordion ---- */
  document.querySelectorAll(".faq-item").forEach((item) => {
    const q = item.querySelector(".faq-q");
    const a = item.querySelector(".faq-a");
    q.addEventListener("click", () => {
      const open = item.classList.contains("open");
      if (open) { item.classList.remove("open"); a.style.maxHeight = 0; }
      else { item.classList.add("open"); a.style.maxHeight = a.scrollHeight + "px"; }
    });
  });

  /* ---- treatment category tabs ---- */
  const tabs = document.querySelectorAll(".tab[data-cat]");
  if (tabs.length) {
    const cards = document.querySelectorAll(".treat-card[data-cat]");
    tabs.forEach((tab) =>
      tab.addEventListener("click", () => {
        tabs.forEach((t) => t.classList.remove("active"));
        tab.classList.add("active");
        const cat = tab.dataset.cat;
        cards.forEach((c) => {
          const show = cat === "all" || c.dataset.cat === cat;
          c.style.display = show ? "" : "none";
        });
      }));
  }

  /* ---- before/after slider ---- */
  document.querySelectorAll(".ba").forEach((ba) => {
    const after = ba.querySelector(".ba__after");
    const handle = ba.querySelector(".ba__handle");
    const range = ba.querySelector(".ba__range");
    const set = (v) => {
      after.style.clipPath = `inset(0 0 0 ${v}%)`;
      handle.style.left = v + "%";
    };
    range?.addEventListener("input", (e) => set(e.target.value));
    set(50);
  });

  /* ---- reveal on scroll ---- */
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add("in"); io.unobserve(e.target); } });
  }, { threshold: 0.12 });
  document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

  /* ============================================================
     BOOKING MODAL — the MioDottore.it 3-step funnel
     ============================================================ */
  const modal = document.querySelector(".modal");
  if (modal) {
    const stepsEls = modal.querySelectorAll(".modal__step");
    const dots = modal.querySelectorAll(".stepper__dot");
    const stepper = modal.querySelector(".stepper");
    let state = { area: null, medico: null, slot: null };

    const labels = {
      visite: "Visite Specialistiche", diagnostica: "Diagnostica per Immagini",
      chirurgia: "Chirurgia Day Surgery", estetica: "Medicina Estetica",
    };

    function show(step) {
      stepsEls.forEach((s) => (s.hidden = +s.dataset.step !== step));
      dots.forEach((d, i) => d.classList.toggle("done", i < step));
      stepper.style.display = step >= 4 ? "none" : "";
    }
    function open(preArea, preMedico) {
      state = { area: preArea || null, medico: preMedico || null, slot: null };
      if (preMedico) { fillStep3(); show(3); }
      else if (preArea) { fillStep2(); show(2); }
      else show(1);
      modal.classList.add("open");
      document.body.style.overflow = "hidden";
    }
    function close() { modal.classList.remove("open"); document.body.style.overflow = ""; }

    const medByArea = {
      visite: ["Dott. Nicola Usai — Cardiologo", "Dott.ssa Chiara Cabras — Endocrinologa", "Dr. Pierluigi Pibi — Andrologia"],
      diagnostica: ["Dr. Maurizio Picciau — Radiologia", "Dott.ssa Elena Serra — Senologia"],
      chirurgia: ["Dott. Antonio Melis — Chirurgo", "Dott.ssa Sara Loi — Anestesista"],
      estetica: ["Dott.ssa Giulia Floris — Medico Estetico", "Dott. Nicola Usai — Medicina Estetica"],
    };

    function fillStep2() {
      const wrap = modal.querySelector('[data-step="2"] .opt-grid');
      const title = modal.querySelector('[data-step="2"] .area-name');
      if (title) title.textContent = labels[state.area] || "";
      wrap.innerHTML = "";
      (medByArea[state.area] || []).forEach((m) => {
        const b = document.createElement("button");
        b.className = "opt";
        b.innerHTML = `<svg width="22" height="22" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M11 14a4 4 0 1 0 0-8 4 4 0 0 0 0 8Z"/><path d="M4 19a7 7 0 0 1 14 0"/></svg><span>${m}</span>`;
        b.addEventListener("click", () => { state.medico = m; fillStep3(); show(3); });
        wrap.appendChild(b);
      });
    }
    function fillStep3() {
      const name = modal.querySelector('[data-step="3"] .medico-name');
      if (name) name.textContent = state.medico || "il primo disponibile";
    }

    // open triggers
    document.querySelectorAll("[data-book]").forEach((b) =>
      b.addEventListener("click", (e) => { e.preventDefault(); open(b.dataset.area, b.dataset.medico); }));

    // step 1 area choice
    modal.querySelectorAll('[data-step="1"] .opt').forEach((o) =>
      o.addEventListener("click", () => { state.area = o.dataset.area; fillStep2(); show(2); }));

    // step 3 slot choice
    modal.querySelectorAll('[data-step="3"] .slot').forEach((s) =>
      s.addEventListener("click", () => {
        modal.querySelectorAll('[data-step="3"] .slot').forEach((x) => x.classList.remove("sel"));
        s.classList.add("sel");
        state.slot = s.textContent;
        const c = modal.querySelector('[data-step="3"] .confirm');
        if (c) c.disabled = false;
      }));
    modal.querySelector('[data-step="3"] .confirm')?.addEventListener("click", () => {
      const r = modal.querySelector('[data-step="4"] .recap');
      if (r) r.textContent = `${state.medico || labels[state.area] || "Visita"} · ${state.slot || ""}`;
      show(4);
    });

    // back buttons
    modal.querySelectorAll("[data-back]").forEach((b) =>
      b.addEventListener("click", () => show(+b.dataset.back)));

    modal.querySelectorAll("[data-close-modal]").forEach((b) => b.addEventListener("click", close));
    modal.querySelector(".modal__scrim")?.addEventListener("click", close);
    document.addEventListener("keydown", (e) => { if (e.key === "Escape") close(); });

    show(1);
  }

  /* ---- doctor page: health icon in hero eyebrow ---- */
  const heroSpec = document.getElementById("heroSpecIcon");
  if (heroSpec && window.specIcon) {
    const spec = heroSpec.getAttribute("data-spec") || "";
    const label = heroSpec.getAttribute("data-spec-label") || spec;
    if (spec) heroSpec.innerHTML = window.specIcon(spec) + " " + label;
  }

  /* ---- render lucide icons if present ---- */
  if (window.lucide) window.lucide.createIcons();
})();
