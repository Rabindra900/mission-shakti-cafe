// Mission Shakti Cafe - Frontend Enhancements
// The site will work even without this file.
// This just adds small UX improvements.

document.addEventListener("DOMContentLoaded", function () {

  /* =====================================================
     1. Highlight current filter chip based on URL (?filter=...)
     ===================================================== */
  const url = new URL(window.location.href);
  const currentFilter = url.searchParams.get("filter") || "All";

  document.querySelectorAll(".filter-chip").forEach((chip) => {
    if (chip.textContent.trim() === currentFilter) {
      chip.classList.add("active");
    } else {
      chip.classList.remove("active");
    }
  });


  /* =====================================================
     2. My Orders page logic
     - Latest order → "Delivered in 30 minutes"
     - Older orders → Delivered
     ===================================================== */
  const orderCards = document.querySelectorAll(".order-card");
  if (orderCards.length > 0) {

    let latestCard = null;
    let latestTime = 0;

    // Find latest order safely
    orderCards.forEach(card => {
      const createdStr = card.dataset.created;
      if (!createdStr) return;

      const createdTime = new Date(createdStr).getTime();
      if (!isNaN(createdTime) && createdTime > latestTime) {
        latestTime = createdTime;
        latestCard = card;
      }
    });

    // Apply status
    orderCards.forEach(card => {
      const orderId = card.id.replace("order-", "");
      const timerEl = document.getElementById("timer-" + orderId);
      const statusEl = document.getElementById("status-" + orderId);

      if (!timerEl || !statusEl) return;

      // Old orders
      if (card !== latestCard) {
        timerEl.textContent = "✅ Your order delivered successfully";
        timerEl.classList.add("delivered-msg");

        statusEl.textContent = "Delivered";
        statusEl.classList.remove("status-pending");
        statusEl.classList.add("status-delivered");
        return;
      }

      // Latest order
      timerEl.innerHTML = "🚚 Your order will be delivered in <b>30 minutes</b>";
      statusEl.textContent = "Preparing";
      statusEl.classList.add("status-pending");
    });
  }


  /* =====================================================
     3. Warn user before leaving checkout page if they changed the form
     ===================================================== */
  const checkoutForm = document.querySelector(".checkout-form");
  if (checkoutForm) {
    let formChanged = false;

    checkoutForm.addEventListener("change", () => {
      formChanged = true;
    });

    checkoutForm.addEventListener("submit", () => {
      formChanged = false;
    });

    window.addEventListener("beforeunload", function (e) {
      if (!formChanged) return;
      e.preventDefault();
      e.returnValue = "";
      return "";
    });
  }
});


/* =====================================================
   4. Auto-trim spaces from phone number input
   ===================================================== */
document.addEventListener("input", function (e) {
  if (e.target.matches('input[type="tel"]')) {
    e.target.value = e.target.value.replace(/\s+/g, "");
  }
});


/* =====================================================
   5. Simple toast helper (for future use)
   ===================================================== */
function showToast(message) {
  console.log("Toast:", message);
  // Later you can replace this with a UI popup
}


/* =====================================================
   OPTIONAL: Add-to-cart click animation (disabled)
   ===================================================== */
// document.addEventListener("click", function (e) {
//   const btn = e.target.closest(".add-to-cart-btn");
//   if (!btn) return;
//   btn.classList.add("clicked");
//   setTimeout(() => btn.classList.remove("clicked"), 200);
// });
