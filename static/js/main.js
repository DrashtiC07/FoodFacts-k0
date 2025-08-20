// Food Scanner - Main JavaScript

document.addEventListener("DOMContentLoaded", () => {
  // Initialize theme
  initializeTheme()

  // Initialize components
  initializeTooltips()
  initializeAlerts()
  initializeAnimations()

  // Add event listeners
  setupEventListeners()
})

// Theme Management
function initializeTheme() {
  const themeToggle = document.getElementById("theme-toggle")
  const currentTheme = localStorage.getItem("theme") || "light"

  // Set initial theme
  document.documentElement.setAttribute("data-theme", currentTheme)
  updateThemeIcon(currentTheme)

  // Theme toggle event listener
  if (themeToggle) {
    themeToggle.addEventListener("click", toggleTheme)
  }
}

function toggleTheme() {
  const currentTheme = document.documentElement.getAttribute("data-theme")
  const newTheme = currentTheme === "dark" ? "light" : "dark"

  // Add transition class for smooth theme change
  document.body.classList.add("theme-transitioning")

  // Change theme
  document.documentElement.setAttribute("data-theme", newTheme)
  localStorage.setItem("theme", newTheme)
  updateThemeIcon(newTheme)

  // Remove transition class after animation
  setTimeout(() => {
    document.body.classList.remove("theme-transitioning")
  }, 300)

  // Dispatch custom event for theme change
  window.dispatchEvent(new CustomEvent("themeChanged", { detail: { theme: newTheme } }))
}

function updateThemeIcon(theme) {
  const themeToggle = document.getElementById("theme-toggle")
  if (themeToggle) {
    const icon = themeToggle.querySelector("i")
    if (icon) {
      icon.className = theme === "dark" ? "bi bi-sun-fill" : "bi bi-moon-fill"
    }
  }
}

// Bootstrap Components Initialization
const bootstrap = window.bootstrap // Declare the bootstrap variable

function initializeTooltips() {
  const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl))
}

function initializeAlerts() {
  // Auto-dismiss alerts after 5 seconds
  const alerts = document.querySelectorAll(".alert:not(.alert-permanent)")
  alerts.forEach((alert) => {
    setTimeout(() => {
      const bsAlert = new bootstrap.Alert(alert)
      bsAlert.close()
    }, 5000)
  })
}

// Animation Utilities
function initializeAnimations() {
  // Intersection Observer for fade-in animations
  const observerOptions = {
    threshold: 0.1,
    rootMargin: "0px 0px -50px 0px",
  }

  const observer = new IntersectionObserver((entries) => {
    entries.forEach((entry) => {
      if (entry.isIntersecting) {
        entry.target.classList.add("fade-in")
        observer.unobserve(entry.target)
      }
    })
  }, observerOptions)

  // Observe elements with animation classes
  document.querySelectorAll(".animate-on-scroll").forEach((el) => {
    observer.observe(el)
  })
}

// Event Listeners
function setupEventListeners() {
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

  // Form validation feedback
  const forms = document.querySelectorAll(".needs-validation")
  forms.forEach((form) => {
    form.addEventListener("submit", (event) => {
      if (!form.checkValidity()) {
        event.preventDefault()
        event.stopPropagation()
      }
      form.classList.add("was-validated")
    })
  })

  // Card hover effects
  const cards = document.querySelectorAll(".card-hover")
  cards.forEach((card) => {
    card.addEventListener("mouseenter", function () {
      this.style.transform = "translateY(-8px)"
    })

    card.addEventListener("mouseleave", function () {
      this.style.transform = "translateY(0)"
    })
  })
}

// Utility Functions
function showNotification(message, type = "info", duration = 3000) {
  const notification = document.createElement("div")
  notification.className = `alert alert-${type} alert-dismissible fade show position-fixed`
  notification.style.cssText = `
        top: 20px;
        right: 20px;
        z-index: 9999;
        min-width: 300px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    `

  notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `

  document.body.appendChild(notification)

  // Auto remove after duration
  setTimeout(() => {
    if (notification.parentNode) {
      notification.remove()
    }
  }, duration)
}

function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M"
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K"
  }
  return num.toString()
}

function debounce(func, wait) {
  let timeout
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// Progress Bar Animation
function animateProgressBar(element, targetWidth, duration = 1000) {
  let start = null
  const startWidth = 0

  function animate(timestamp) {
    if (!start) start = timestamp
    const progress = timestamp - start
    const percentage = Math.min(progress / duration, 1)

    const currentWidth = startWidth + (targetWidth - startWidth) * percentage
    element.style.width = currentWidth + "%"

    if (percentage < 1) {
      requestAnimationFrame(animate)
    }
  }

  requestAnimationFrame(animate)
}

// Health Score Color Helper
function getHealthScoreClass(score) {
  if (score >= 80) return "health-score-excellent"
  if (score >= 60) return "health-score-good"
  if (score >= 40) return "health-score-fair"
  return "health-score-poor"
}

function getHealthScoreText(score) {
  if (score >= 80) return "Excellent"
  if (score >= 60) return "Good"
  if (score >= 40) return "Fair"
  return "Poor"
}

// Export functions for use in other scripts
window.FoodScanner = {
  showNotification,
  formatNumber,
  debounce,
  animateProgressBar,
  getHealthScoreClass,
  getHealthScoreText,
  toggleTheme,
}
