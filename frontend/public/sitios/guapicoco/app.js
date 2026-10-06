// Guapi Coco · Tienda (catálogo, carrito con persistencia y pedido por WhatsApp)
const WHATSAPP = "573000000000";

const PRODUCTS = [
  { id: "coco-verde", name: "Coco Verde Fresco", cat: "fresco", catLabel: "Fresco", price: 4500, unit: "unidad", img: "img/coco_fresco.jpg", desc: "Coco tierno recién cosechado, ideal para tomar directamente de la fruta.", badge: "Más vendido" },
  { id: "agua-coco", name: "Agua de Coco Natural", cat: "bebidas", catLabel: "Bebidas", price: 8000, unit: "botella 500 ml", img: "img/agua_coco.jpg", desc: "100% agua de coco embotellada el mismo día. Hidratación natural sin azúcar añadida.", badge: "Nuevo" },
  { id: "aceite-virgen", name: "Aceite de Coco Virgen", cat: "cocina", catLabel: "Cocina & Cuidado", price: 28000, unit: "frasco 350 g", img: "img/aceite_coco.jpg", desc: "Prensado en frío. Perfecto para cocinar, el cabello y el cuidado de la piel." },
  { id: "leche-coco", name: "Leche de Coco Artesanal", cat: "cocina", catLabel: "Cocina & Cuidado", price: 12000, unit: "botella 500 ml", img: "img/leche_coco.jpg", desc: "Cremosa y espesa, para arroz con coco, postres, sopas y batidos." },
  { id: "cocadas", name: "Cocadas de la Abuela", cat: "dulces", catLabel: "Dulces", price: 10000, unit: "caja x6", img: "img/cocadas.jpg", desc: "Receta tradicional con coco rallado y panela. Horneadas en pequeños lotes.", badge: "Artesanal" },
  { id: "coco-rallado", name: "Coco Rallado Deshidratado", cat: "dulces", catLabel: "Dulces", price: 9000, unit: "bolsa 250 g", img: "img/coco_rallado.jpg", desc: "Para repostería, granolas y toppings. Sin azúcar ni conservantes." },
];

const $ = (s) => document.querySelector(s);
const fmt = (n) => "$" + n.toLocaleString("es-CO");
let cart = JSON.parse(localStorage.getItem("gc_cart") || "{}");

// ---- Catálogo ----
function renderProducts(filter = "todos") {
  const list = filter === "todos" ? PRODUCTS : PRODUCTS.filter((p) => p.cat === filter);
  $("#products-grid").innerHTML = list.map((p, i) => `
    <article class="product" style="animation-delay:${i * 70}ms">
      <div class="product-img">
        <img src="${p.img}" alt="${p.name}" loading="lazy" />
        ${p.badge ? `<span class="badge">${p.badge}</span>` : ""}
      </div>
      <div class="product-body">
        <span class="product-cat">${p.catLabel}</span>
        <h3>${p.name}</h3>
        <p>${p.desc}</p>
        <div class="product-foot">
          <span class="price">${fmt(p.price)} <small>/ ${p.unit}</small></span>
          <button class="add-btn" id="add-${p.id}" data-add="${p.id}" aria-label="Agregar ${p.name}">+</button>
        </div>
      </div>
    </article>`).join("");
}

$("#filters").addEventListener("click", (e) => {
  const chip = e.target.closest(".chip");
  if (!chip) return;
  document.querySelectorAll(".chip").forEach((c) => c.classList.toggle("active", c === chip));
  renderProducts(chip.dataset.filter);
});

$("#products-grid").addEventListener("click", (e) => {
  const btn = e.target.closest("[data-add]");
  if (!btn) return;
  const id = btn.dataset.add;
  cart[id] = (cart[id] || 0) + 1;
  saveCart();
  toast(`${PRODUCTS.find((p) => p.id === id).name} agregado 🥥`);
  const badge = $("#cart-count");
  badge.classList.add("bump");
  setTimeout(() => badge.classList.remove("bump"), 300);
});

// ---- Carrito ----
function saveCart() {
  Object.keys(cart).forEach((k) => cart[k] <= 0 && delete cart[k]);
  localStorage.setItem("gc_cart", JSON.stringify(cart));
  renderCart();
}

function renderCart() {
  const entries = Object.entries(cart);
  const count = entries.reduce((a, [, q]) => a + q, 0);
  const total = entries.reduce((a, [id, q]) => a + PRODUCTS.find((p) => p.id === id).price * q, 0);
  $("#cart-count").textContent = count;
  $("#cart-total").textContent = fmt(total);
  $("#checkout-btn").disabled = count === 0;
  $("#checkout-btn").style.opacity = count === 0 ? 0.5 : 1;
  $("#cart-items").innerHTML = entries.length === 0
    ? `<div class="cart-empty"><span>🥥</span>Tu carrito está vacío.<br/>¡Agrega algo delicioso!</div>`
    : entries.map(([id, q]) => {
        const p = PRODUCTS.find((x) => x.id === id);
        return `<div class="cart-item">
          <img src="${p.img}" alt="${p.name}" />
          <div><b>${p.name}</b><small>${fmt(p.price)} · ${p.unit}</small></div>
          <div class="qty"><button data-dec="${id}" aria-label="Quitar">−</button><span>${q}</span><button data-inc="${id}" aria-label="Agregar">+</button></div>
        </div>`;
      }).join("");
}

$("#cart-items").addEventListener("click", (e) => {
  const inc = e.target.dataset.inc, dec = e.target.dataset.dec;
  if (inc) cart[inc]++;
  if (dec) cart[dec]--;
  if (inc || dec) saveCart();
});

const openCart = (open) => {
  $("#cart").classList.toggle("open", open);
  $("#overlay").classList.toggle("show", open);
};
$("#cart-open-btn").onclick = () => openCart(true);
$("#cart-close-btn").onclick = () => openCart(false);
$("#overlay").onclick = () => openCart(false);

$("#checkout-btn").onclick = () => {
  const lines = Object.entries(cart).map(([id, q]) => {
    const p = PRODUCTS.find((x) => x.id === id);
    return `• ${q} x ${p.name} (${p.unit}) — ${fmt(p.price * q)}`;
  });
  const total = Object.entries(cart).reduce((a, [id, q]) => a + PRODUCTS.find((p) => p.id === id).price * q, 0);
  const msg = `¡Hola Guapi Coco! 🥥 Quiero hacer este pedido:\n\n${lines.join("\n")}\n\n*Total: ${fmt(total)}*\n\nMi nombre y dirección de entrega:`;
  window.open(`https://wa.me/${WHATSAPP}?text=${encodeURIComponent(msg)}`, "_blank");
};

// ---- Utilidades UI ----
let toastTimer;
function toast(text) {
  const t = $("#toast");
  t.textContent = text;
  t.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => t.classList.remove("show"), 2200);
}

window.addEventListener("scroll", () => $("#nav").classList.toggle("scrolled", window.scrollY > 10));

$("#menu-btn").onclick = () => $("#nav-links").classList.toggle("open");
document.querySelectorAll("#nav-links a").forEach((a) => a.addEventListener("click", () => $("#nav-links").classList.remove("open")));

$("#contact-form").addEventListener("submit", (e) => {
  e.preventDefault();
  e.target.reset();
  $("#form-ok").hidden = false;
  setTimeout(() => ($("#form-ok").hidden = true), 4000);
});

// Animación de aparición + contadores del hero
const io = new IntersectionObserver((entries) => {
  entries.forEach((en) => {
    if (!en.isIntersecting) return;
    en.target.classList.add("in");
    en.target.querySelectorAll("[data-count]").forEach(animateCount);
    io.unobserve(en.target);
  });
}, { threshold: 0.15 });
document.querySelectorAll(".reveal").forEach((el) => io.observe(el));

function animateCount(el) {
  const end = +el.dataset.count, start = performance.now(), dur = 1400;
  const step = (now) => {
    const k = Math.min(1, (now - start) / dur);
    el.textContent = Math.round(end * (1 - Math.pow(1 - k, 3)));
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

renderProducts();
renderCart();
