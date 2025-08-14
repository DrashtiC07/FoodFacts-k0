// Theme Toggle and Base Functionality
document.addEventListener("DOMContentLoaded", () => {
  const themeToggle = document.getElementById("themeToggle")
  const themeIcon = document.getElementById("themeIcon")
  const html = document.documentElement

  // Check for saved theme preference
  const currentTheme = localStorage.getItem("theme") || "light"
  html.setAttribute("data-bs-theme", currentTheme)
  updateThemeIcon(currentTheme)

  if (themeToggle) {
    themeToggle.addEventListener("click", () => {
      const newTheme = html.getAttribute("data-bs-theme") === "dark" ? "light" : "dark"
      html.setAttribute("data-bs-theme", newTheme)
      localStorage.setItem("theme", newTheme)
      updateThemeIcon(newTheme)
    })
  }

  function updateThemeIcon(theme) {
    if (themeIcon) {
      themeIcon.className = theme === "light" ? "bi bi-moon-fill" : "bi bi-sun-fill"
    }
  }

  // Auto-dismiss alerts
  const alerts = document.querySelectorAll(".alert")
  alerts.forEach((alert) => {
    if (!alert.querySelector(".btn-close")) {
      setTimeout(() => {
        alert.style.opacity = "0"
        alert.style.transform = "translateY(-20px)"
        setTimeout(() => {
          alert.remove()
        }, 300)
      }, 5000)
    }
  })

  // Smooth scrolling for anchor links
  document.querySelectorAll('a[href^="#"]').forEach((anchor) => {
    anchor.addEventListener("click", function (e) {
      e.preventDefault()
      const target = document.querySelector(this.getAttribute("href"))
      if (target) {
        target.scrollIntoView({
          behavior: "smooth",
          block: "start",
        })
      }
    })
  })

  // Loading states for forms
  const forms = document.querySelectorAll("form")
  forms.forEach((form) => {
    form.addEventListener("submit", () => {
      const submitBtn = form.querySelector('button[type="submit"]')
      if (submitBtn) {
        submitBtn.disabled = true
        submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm me-2"></span>Loading...'
      }
    })
  })

  // Enhanced card hover effects
  const cards = document.querySelectorAll(".card")
  cards.forEach((card) => {
    card.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-5px)"
    })

    card.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0)"
    })
  })

  // Search functionality enhancement
  const searchInputs = document.querySelectorAll('input[type="search"]')
  searchInputs.forEach((input) => {
    let searchTimeout
    input.addEventListener("input", function () {
      clearTimeout(searchTimeout)
      searchTimeout = setTimeout(() => {
        console.log("Searching for:", this.value)
      }, 300)
    })
  })

  // Keyboard shortcuts
  document.addEventListener("keydown", (e) => {
    // Ctrl/Cmd + K for search
    if ((e.ctrlKey || e.metaKey) && e.key === "k") {
      e.preventDefault()
      const searchInput = document.querySelector('input[type="search"]')
      if (searchInput) {
        searchInput.focus()
      }
    }
  })

  // Error handling for images
  document.addEventListener(
    "error",
    (e) => {
      if (e.target.tagName === "IMG") {
        e.target.src =
          "data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='60' height='60' viewBox='0 0 24 24' fill='none' stroke='%23ccc' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'%3E%3Crect x='3' y='3' width='18' height='18' rx='2' ry='2'/%3E%3Ccircle cx='8.5' cy='8.5' r='1.5'/%3E%3Cpolyline points='21,15 16,10 5,21'/%3E%3C/svg%3E"
        e.target.alt = "Image not available"
      }
    },
    true,
  )
})

// Utility functions
function showToast(message, type = "info") {
  const toastContainer = document.querySelector(".toast-container") || createToastContainer()
  const toast = createToast(message, type)
  toastContainer.appendChild(toast)

  const bsToast = new window.bootstrap.Toast(toast)
  bsToast.show()

  toast.addEventListener("hidden.bs.toast", () => {
    toast.remove()
  })
}

function createToastContainer() {
  const container = document.createElement("div")
  container.className = "toast-container position-fixed top-0 end-0 p-3"
  container.style.zIndex = "1055"
  document.body.appendChild(container)
  return container
}

function createToast(message, type) {
  const toast = document.createElement("div")
  toast.className = "toast"
  toast.setAttribute("role", "alert")
  toast.innerHTML = `
      <div class="toast-header">
          <i class="bi bi-${getToastIcon(type)} me-2 text-${type}"></i>
          <strong class="me-auto">Food Facts Scanner</strong>
          <button type="button" class="btn-close" data-bs-dismiss="toast"></button>
      </div>
      <div class="toast-body">
          ${message}
      </div>
  `
  return toast
}

function getToastIcon(type) {
  const icons = {
    success: "check-circle",
    error: "exclamation-circle",
    warning: "exclamation-triangle",
    info: "info-circle",
  }
  return icons[type] || "info-circle"
}
