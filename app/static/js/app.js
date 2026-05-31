document.addEventListener("click", (event) => {
  if (event.target.closest("[data-table-action]")) {
    event.stopPropagation();
  }

  const openButton = event.target.closest("[data-open-modal]");
  if (openButton) {
    const modal = document.getElementById(openButton.dataset.openModal);
    if (modal) {
      modal.classList.add("is-open");
      modal.setAttribute("aria-hidden", "false");
      const input = modal.querySelector("input");
      if (input) input.focus();
    }
  }

  if (event.target.matches("[data-close-modal]") || event.target.classList.contains("modal")) {
    const modal = event.target.closest(".modal");
    if (modal) {
      modal.classList.remove("is-open");
      modal.setAttribute("aria-hidden", "true");
    }
  }
});

document.addEventListener("keydown", (event) => {
  if (event.key !== "Escape") return;
  document.querySelectorAll(".modal.is-open").forEach((modal) => {
    modal.classList.remove("is-open");
    modal.setAttribute("aria-hidden", "true");
  });
});

const initCustomerSearch = () => {
  const customerSearch = document.querySelector("[data-customer-search]");
  if (!customerSearch) return;

  const form = customerSearch.querySelector("[data-customer-search-form]");
  const input = customerSearch.querySelector("[data-customer-search-input]");
  const results = customerSearch.querySelector("[data-customer-search-results]");
  if (!form || !input || !results) return;

  let activeRequest;

  const hideResults = () => {
    results.hidden = true;
    results.replaceChildren();
  };

  const showEmptyResults = () => {
    const empty = document.createElement("div");
    empty.className = "customer-search-empty";
    empty.textContent = "لا توجد نتائج";
    results.replaceChildren(empty);
    results.hidden = false;
  };

  const showCustomers = (customers) => {
    if (!customers.length) {
      showEmptyResults();
      return;
    }

    const list = document.createElement("div");
    list.className = "customer-search-list";
    customers.forEach((customer) => {
      const link = document.createElement("a");
      link.href = `/customers/${customer.id}`;
      link.className = "customer-search-result";
      link.textContent = customer.customer_name;
      list.appendChild(link);
    });
    results.replaceChildren(list);
    results.hidden = false;
  };

  const runSearch = async () => {
    const query = input.value.trim();
    if (activeRequest) activeRequest.abort();
    if (!query) {
      hideResults();
      return;
    }

    activeRequest = new AbortController();
    try {
      const response = await fetch(`/customers/search?q=${encodeURIComponent(query)}`, {
        headers: { Accept: "application/json" },
        signal: activeRequest.signal,
      });
      if (!response.ok) {
        showEmptyResults();
        return;
      }

      const data = await response.json();
      const customers = Array.isArray(data) ? data : data.customers;
      showCustomers(Array.isArray(customers) ? customers : []);
    } catch (error) {
      if (error.name === "AbortError") return;
      showEmptyResults();
    }
  };

  input.addEventListener("input", runSearch);
  form.addEventListener("submit", (event) => {
    event.preventDefault();
    runSearch();
  });

  document.addEventListener("click", (event) => {
    if (!customerSearch.contains(event.target)) hideResults();
  });
};

if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", initCustomerSearch);
} else {
  initCustomerSearch();
}
