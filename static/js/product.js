import { Chart } from "@/components/ui/chart"

document.addEventListener("DOMContentLoaded", () => {
  // Import Bootstrap
  const bootstrap = window.bootstrap

  // Initialize Bootstrap tooltips
  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
  var tooltipList = tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl))

  // Theme toggle functionality
  const themeToggleBtn = document.getElementById("theme-toggle")
  if (themeToggleBtn) {
    themeToggleBtn.addEventListener("click", () => {
      const currentTheme = document.documentElement.getAttribute("data-bs-theme")
      const newTheme = currentTheme === "dark" ? "light" : "dark"
      document.documentElement.setAttribute("data-bs-theme", newTheme)
      localStorage.setItem("theme", newTheme) // Save preference
      updateThemeIcon(newTheme)
    })

    // Set initial theme based on localStorage or system preference
    const savedTheme = localStorage.getItem("theme")
    if (savedTheme) {
      document.documentElement.setAttribute("data-bs-theme", savedTheme)
      updateThemeIcon(savedTheme)
    } else if (window.matchMedia && window.matchMedia("(prefers-color-scheme: dark)").matches) {
      document.documentElement.setAttribute("data-bs-theme", "dark")
      updateThemeIcon("dark")
    } else {
      document.documentElement.setAttribute("data-bs-theme", "light")
      updateThemeIcon("light")
    }
  }

  function updateThemeIcon(theme) {
    const icon = themeToggleBtn ? themeToggleBtn.querySelector("i") : null
    if (icon) {
      if (theme === "dark") {
        icon.classList.remove("bi-sun-fill")
        icon.classList.add("bi-moon-fill")
      } else {
        icon.classList.remove("bi-moon-fill")
        icon.classList.add("bi-sun-fill")
      }
    }
  }

  // Scroll animations (fade-in effect)
  const faders = document.querySelectorAll(".fade-in")
  const appearOptions = {
    threshold: 0.1,
    rootMargin: "0px 0px -50px 0px",
  }

  const appearOnScroll = new IntersectionObserver((entries, appearOnScroll) => {
    entries.forEach((entry) => {
      if (!entry.isIntersecting) {
        return
      } else {
        entry.target.classList.add("visible")
        appearOnScroll.unobserve(entry.target)
      }
    })
  }, appearOptions)

  faders.forEach((fader) => {
    appearOnScroll.observe(fader)
  })

  // Ripple effect for buttons
  document
    .querySelectorAll(".enhanced-btn, .modern-nav-btn, .theme-toggle-btn, .user-dropdown-toggle")
    .forEach((button) => {
      button.addEventListener("click", function (e) {
        const x = e.clientX - e.target.getBoundingClientRect().left
        const y = e.clientY - e.target.getBoundingClientRect().top

        const ripple = document.createElement("span")
        ripple.classList.add("ripple")
        ripple.style.left = x + "px"
        ripple.style.top = y + "px"
        this.appendChild(ripple)

        ripple.addEventListener("animationend", function () {
          this.remove()
        })
      })
    })

  // Product Detail Page Specifics
  const healthScoreChartCanvas = document.getElementById("healthScoreChart")
  if (healthScoreChartCanvas) {
    const healthScoreValue = Number.parseInt(document.getElementById("healthScoreValue").textContent.trim())
    const healthScoreTextElement = document.getElementById("healthScoreValue")

    let scoreColor = "#ccc" // Default grey
    if (healthScoreValue >= 0) {
      // Assuming Nutri-Score A-E, A is best (negative score), E is worst (positive score)
      // Nutri-Score typically ranges from -15 (best) to +40 (worst)
      // We'll map this to a color scale. Let's simplify for now based on common interpretation.
      if (healthScoreValue <= 0) {
        // A
        scoreColor = "#28a745" // Green
      } else if (healthScoreValue <= 5) {
        // B
        scoreColor = "#66bb6a" // Light Green
      } else if (healthScoreValue <= 10) {
        // C
        scoreColor = "#ffc107" // Yellow
      } else if (healthScoreValue <= 15) {
        // D
        scoreColor = "#fd7e14" // Orange
      } else {
        // E
        scoreColor = "#dc3545" // Red
      }
    }

    const healthScoreChart = new Chart(healthScoreChartCanvas, {
      type: "doughnut",
      data: {
        datasets: [
          {
            data: [healthScoreValue, 40 - healthScoreValue], // Assuming max score is 40 for visualization
            backgroundColor: [scoreColor, "rgba(204, 204, 204, 0.2)"],
            borderWidth: 0,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: "80%",
        plugins: {
          tooltip: {
            enabled: false,
          },
          legend: {
            display: false,
          },
        },
        animation: {
          animateRotate: true,
          animateScale: true,
          duration: 800, // Reduced from 1500
          easing: "easeOutQuart",
        },
      },
    })

    // Animate the score text
    if (healthScoreValue !== "N/A") {
      let currentScore = 0
      const targetScore = healthScoreValue
      const duration = 800 // Match chart animation duration
      const stepTime = 10 // ms per step
      const steps = duration / stepTime
      const increment = targetScore / steps

      const animateScore = () => {
        currentScore += increment
        if (currentScore < targetScore) {
          healthScoreTextElement.textContent = Math.round(currentScore)
          requestAnimationFrame(animateScore)
        } else {
          healthScoreTextElement.textContent = targetScore
        }
      }
      requestAnimationFrame(animateScore)
    }
  }

  // Review star rating functionality
  const ratingStars = document.getElementById("ratingStars")
  const ratingInput = document.getElementById("ratingInput")

  if (ratingStars && ratingInput) {
    let currentRating = 0

    ratingStars.addEventListener("mouseover", (e) => {
      if (e.target.tagName === "I") {
        const hoverRating = Number.parseInt(e.target.dataset.rating)
        updateStarDisplay(hoverRating)
      }
    })

    ratingStars.addEventListener("mouseout", () => {
      updateStarDisplay(currentRating)
    })

    ratingStars.addEventListener("click", (e) => {
      if (e.target.tagName === "I") {
        currentRating = Number.parseInt(e.target.dataset.rating)
        ratingInput.value = currentRating
        updateStarDisplay(currentRating)
      }
    })

    function updateStarDisplay(rating) {
      Array.from(ratingStars.children).forEach((star, index) => {
        if (index < rating) {
          star.classList.remove("bi-star")
          star.classList.add("bi-star-fill")
        } else {
          star.classList.remove("bi-star-fill")
          star.classList.add("bi-star")
        }
      })
    }
  }
})
