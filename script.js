document.addEventListener("DOMContentLoaded", () => {
  const year = document.getElementById("year");
  if (year) {
    year.textContent = new Date().getFullYear();
  }

  const curatedProducts = [
    {
      title: "Vera Bradley satchel + wallet",
      price: "$25.98",
      url: "https://www.depop.com/products/zoessorenson-vera-bradley-bag-with-2/",
      image: "https://media-photos.depop.com/b1/34544665/3156885948_ea31beb4d4d443668710b7549ca88b66/P0.jpg",
      description: "Floral overnight-sized bag with both top handles and a crossbody strap. Matching wallet included.",
      category: "accessories",
      tag: "Bag drop"
    },
    {
      title: "Red Hollister V-neck sweater",
      price: "$32.00",
      url: "https://www.depop.com/products/zoessorenson-red-hollister-co-v-neck-sweater/",
      image: "https://media-photos.depop.com/b1/34544665/3156880933_c5c2c841ed8b4fcf8aae3f82a0048b6d/P0.jpg",
      description: "Soft rib knit with a deep neckline. Perfect layered over a slip or worn solo.",
      category: "tops",
      tag: "Knitwear"
    },
    {
      title: "L.L. Bean sweat shorts (M)",
      price: "$10.00",
      url: "https://www.depop.com/products/zoessorenson-ll-bean-sweat-shorts-size/",
      image: "https://media-photos.depop.com/b1/34544665/3109706700_d0fb393dc2704837897b127c2d6a1d40/P0.jpg",
      description: "Boxy mid-rise fit with pockets. Made for off-duty coffee runs.",
      category: "bottoms",
      tag: "Weekend set"
    },
    {
      title: "Striped cropped tee",
      price: "$9.99",
      url: "https://www.depop.com/products/zoessorenson-cropped-white-and-black-stripe/",
      image: "https://media-photos.depop.com/b1/34544665/3081083372_cdc188864bbc4be89dd32551acd579af/P0.jpg",
      description: "White + black rib tee that hits right at the waist. Looks ace with cargos.",
      category: "tops",
      tag: "Everyday top"
    },
    {
      title: "Brown + white fuzzy knit",
      price: "$15.88",
      url: "https://www.depop.com/products/zoessorenson-super-cute-brown-and-white/",
      image: "https://media-photos.depop.com/b1/34544665/3069696416_6b55349fc5f647308bd4cf9896f05b40/P0.jpg",
      description: "Cow-print inspired sweater vest that layers over tees and dresses.",
      category: "tops",
      tag: "Statement knit"
    },
    {
      title: "Pattern windbreaker shell",
      price: "$20.22",
      url: "https://www.depop.com/products/zoessorenson-cool-pattern-wind-jacket-shell/",
      image: "https://media-photos.depop.com/b1/34544665/3030475815_b81c1f148230453198136c838404f862/P0.jpg",
      description: "90s shell jacket with teal + lilac print. Lightweight and oversized.",
      category: "outerwear",
      tag: "Outerwear"
    },
    {
      title: "Black & gold pearl necklace",
      price: "$10.10",
      url: "https://www.depop.com/products/zoessorenson-black-and-gold-pearl-necklace-adfc/",
      image: "https://media-photos.depop.com/b1/34544665/3030620594_e8dbe41eadca419ca8f517c9ef6ba325/P0.jpg",
      description: "Layer-friendly necklace featuring alternating pearls and gold beads.",
      category: "accessories",
      tag: "Jewelry"
    },
    {
      title: "Faux fur lined suede coat",
      price: "$70.00",
      url: "https://www.depop.com/products/zoessorenson-brown-faux-fur-lined-suede/",
      image: "https://media-photos.depop.com/b1/34544665/3020548832_69dbbb5180834b43a63b1fef382af78c/P0.jpg",
      description: "Chocolate brown suede with plush lining — the coziest winter staple.",
      category: "outerwear",
      tag: "Winter edit"
    }
  ];

  const productGrid = document.getElementById("depop-grid");
  const filterButtons = document.querySelectorAll(".filter-btn");

  const renderProducts = (category = "all") => {
    if (!productGrid) return;
    const filtered = curatedProducts.filter((item) => category === "all" || item.category === category);

    if (!filtered.length) {
      productGrid.innerHTML = '<p class="note">No listings match that filter right now — DM me on Depop for first dibs.</p>';
      return;
    }

    const markup = filtered
      .map((item) => {
        return `
          <article class="product-card" data-category="${item.category}">
            <img src="${item.image}" alt="${item.title}" loading="lazy" />
            <div class="product-card__body">
              <p class="eyebrow">${item.tag}</p>
              <h4>${item.title}</h4>
              <p class="product-card__meta">${item.description}</p>
              <p class="price">${item.price}</p>
              <div class="product-card__actions">
                <a class="btn ghost small" href="${item.url}" target="_blank" rel="noreferrer">View on Depop</a>
              </div>
            </div>
          </article>
        `;
      })
      .join("");

    productGrid.innerHTML = markup;
  };

  if (filterButtons.length && productGrid) {
    filterButtons.forEach((btn) => {
      btn.addEventListener("click", () => {
        filterButtons.forEach((button) => button.classList.remove("active"));
        btn.classList.add("active");
        renderProducts(btn.dataset.filter || "all");
      });
    });
  }

  renderProducts();

  const form = document.getElementById("rsvp-form");
  if (form) {
    const feedback = form.querySelector(".form-feedback");
    form.addEventListener("submit", (event) => {
      event.preventDefault();
      const formData = new FormData(form);
      const name = formData.get("name");
      feedback.textContent = `Thanks, ${name || "friend"}! I'll reply via email or Depop ASAP.`;
      form.reset();
    });
  }
});
