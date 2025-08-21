// Dashboard JavaScript Functions
document.addEventListener("DOMContentLoaded", () => {
  console.log("Dashboard JavaScript loaded")

  // Export Nutrition Data Function
  window.exportNutritionData = () => {
    // Create a form and submit it to trigger PDF download
    const form = document.createElement("form")
    form.method = "POST"
    form.action = "/accounts/export-nutrition-data/"

    // Add CSRF token
    const csrfToken =
      document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
      document.querySelector('meta[name="csrf-token"]')?.getAttribute("content")
    if (csrfToken) {
      const csrfInput = document.createElement("input")
      csrfInput.type = "hidden"
      csrfInput.name = "csrfmiddlewaretoken"
      csrfInput.value = csrfToken
      form.appendChild(csrfInput)
    }

    document.body.appendChild(form)
    form.submit()
    document.body.removeChild(form)
  }

  // Remove Tracked Item Function
  window.removeTrackedItem = (itemId, itemType) => {
    if (!confirm("Are you sure you want to remove this item?")) {
      return
    }

    const formData = new FormData()
    formData.append("item_id", itemId)
    formData.append("item_type", itemType)
    formData.append(
      "csrfmiddlewaretoken",
      document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
        document.querySelector('meta[name="csrf-token"]')?.getAttribute("content"),
    )

    fetch("/accounts/remove-tracked-item/", {
      method: "POST",
      body: formData,
      headers: {
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Remove the item from the UI
          const itemElement = document.querySelector(`[data-item-id="${itemId}"]`)
          if (itemElement) {
            itemElement.remove()
          }

          // Update progress bars if needed
          if (data.progress) {
            updateProgressBars(data.progress)
          }

          // Show success message
          showAlert("Item removed successfully!", "success")
        } else {
          showAlert(data.message || "Error removing item", "danger")
        }
      })
      .catch((error) => {
        console.error("Error:", error)
        showAlert("Error removing item", "danger")
      })
  }

  // Refresh Personalized Tips Function
  window.refreshPersonalizedTips = () => {
    const button = document.querySelector('[onclick*="refreshPersonalizedTips"]')
    const originalText = button ? button.innerHTML : ""

    if (button) {
      button.innerHTML = '<span class="spinner"></span> Loading...'
      button.disabled = true
    }

    fetch("/accounts/refresh-tips/", {
      method: "POST",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken":
          document.querySelector("[name=csrfmiddlewaretoken]")?.value ||
          document.querySelector('meta[name="csrf-token"]')?.getAttribute("content"),
      },
    })
      .then((response) => response.json())
      .then((data) => {
        if (data.success) {
          // Update tips content
          const tipsContainer = document.getElementById("personalizedTipsContent")
          if (tipsContainer && data.tips_html) {
            tipsContainer.innerHTML = data.tips_html
          }
          showAlert("Tips refreshed successfully!", "success")
        } else {
          showAlert(data.message || "Error refreshing tips", "danger")
        }
      })
      .catch((error) => {
        console.error("Error:", error)
        showAlert("Error refreshing tips", "danger")
      })
      .finally(() => {
        if (button) {
          button.innerHTML = originalText
          button.disabled = false
        }
      })
  }

  // Update Progress Bars Function
  function updateProgressBars(progressData) {
    console.log("Updating progress bars with data:", progressData)

    Object.keys(progressData).forEach((nutrient) => {
      const progressBar = document.querySelector(`#${nutrient}Progress`)
      const progressText = document.querySelector(`#${nutrient}Text`)

      if (progressBar && progressData[nutrient] !== undefined) {
        const percentage = Math.min(progressData[nutrient], 100)
        progressBar.style.width = percentage + "%"
        progressBar.setAttribute("aria-valuenow", percentage)

        // Update progress bar color based on percentage
        progressBar.className = "progress-bar"
        if (percentage >= 100) {
          progressBar.classList.add("bg-success")
        } else if (percentage >= 75) {
          progressBar.classList.add("bg-warning")
        } else {
          progressBar.classList.add("bg-info")
        }
      }

      if (progressText) {
        progressText.textContent = `${Math.round(progressData[nutrient])}%`
      }
    })
  }

  // Update Personalized Tips Function
  function updatePersonalizedTips(progressData) {
    console.log("Updating personalized tips with progress data:", progressData)

    // This function can be expanded to generate dynamic tips based on progress
    const tipsContainer = document.getElementById("personalizedTipsContent")
    if (tipsContainer && progressData) {
      // Add logic to update tips based on current progress
      // For now, just refresh the existing tips
      window.refreshPersonalizedTips()
    }
  }

  // Show Alert Function
  function showAlert(message, type = "info") {
    const alertContainer = document.getElementById("alertContainer") || document.body
    const alert = document.createElement("div")
    alert.className = `alert alert-${type} alert-dismissible fade show`
    alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `

    alertContainer.appendChild(alert)

    // Auto-dismiss after 5 seconds
    setTimeout(() => {
      if (alert.parentNode) {
        alert.remove()
      }
    }, 5000)
  }

  // Initialize Dashboard Features
  function initializeDashboard() {
    // Animate progress bars on load
    const progressBars = document.querySelectorAll(".progress-bar")
    progressBars.forEach((bar) => {
      const width = bar.getAttribute("aria-valuenow") || 0
      bar.style.width = "0%"
      setTimeout(() => {
        bar.style.width = width + "%"
      }, 500)
    })

    // Initialize tooltips if Bootstrap is available
    const bootstrap = window.bootstrap // Declare bootstrap variable
    if (typeof bootstrap !== "undefined") {
      const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
      tooltipTriggerList.map((tooltipTriggerEl) => new bootstrap.Tooltip(tooltipTriggerEl))
    }

    // Protect personalized tips from disappearing
    const personalizedTipsContent = document.getElementById("personalizedTipsContent")
    if (personalizedTipsContent) {
      // Create a MutationObserver to prevent tips from being hidden
      const observer = new MutationObserver((mutations) => {
        mutations.forEach((mutation) => {
          if (mutation.type === "childList" || mutation.type === "attributes") {
            // Ensure tips remain visible
            const tips = personalizedTipsContent.querySelectorAll(".alert")
            tips.forEach((tip) => {
              if (tip.style.display === "none" && !tip.hasAttribute("data-user-dismissed")) {
                tip.style.display = ""
              }
            })
          }
        })
      })

      observer.observe(personalizedTipsContent, {
        childList: true,
        subtree: true,
        attributes: true,
        attributeFilter: ["style", "class"],
      })
    }
  }

  // Initialize dashboard when DOM is ready
  initializeDashboard()

  // Make functions globally available
  window.updateProgressBars = updateProgressBars
  window.updatePersonalizedTips = updatePersonalizedTips
  window.showAlert = showAlert
})

// Additional utility functions for dashboard
function formatNumber(num) {
  if (num >= 1000000) {
    return (num / 1000000).toFixed(1) + "M"
  } else if (num >= 1000) {
    return (num / 1000).toFixed(1) + "K"
  }
  return num.toString()
}

function calculatePercentage(current, target) {
  if (target === 0) return 0
  return Math.min((current / target) * 100, 100)
}

// Export functions for use in other scripts
window.dashboardUtils = {
  formatNumber,
  calculatePercentage,
  updateProgressBars: window.updateProgressBars,
  showAlert: window.showAlert,
}
