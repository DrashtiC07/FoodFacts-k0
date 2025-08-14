// Scanner Specific JavaScript

document.addEventListener("DOMContentLoaded", () => {
  initializeScanner()
  initializeFileUpload()
  initializeManualEntry()
})

function initializeScanner() {
  const scanForm = document.getElementById("scan-form")
  const fileInput = document.getElementById("image-input")
  const dropZone = document.getElementById("drop-zone")
  const previewContainer = document.getElementById("preview-container")

  if (!scanForm || !fileInput || !dropZone) return

  // File input change handler
  fileInput.addEventListener("change", handleFileSelect)

  // Drag and drop handlers
  dropZone.addEventListener("dragover", handleDragOver)
  dropZone.addEventListener("dragleave", handleDragLeave)
  dropZone.addEventListener("drop", handleFileDrop)

  // Form submission
  scanForm.addEventListener("submit", handleScanSubmit)
}

function initializeFileUpload() {
  const uploadBtn = document.getElementById("upload-btn")
  const fileInput = document.getElementById("image-input")

  if (uploadBtn && fileInput) {
    uploadBtn.addEventListener("click", () => fileInput.click())
  }
}

function initializeManualEntry() {
  const manualEntryBtn = document.getElementById("manual-entry-btn")
  const manualEntryForm = document.getElementById("manual-entry-form")
  const barcodeInput = document.getElementById("barcode-input")

  if (manualEntryBtn && manualEntryForm) {
    manualEntryBtn.addEventListener("click", () => {
      manualEntryForm.style.display = manualEntryForm.style.display === "none" ? "block" : "none"
      if (manualEntryForm.style.display === "block" && barcodeInput) {
        barcodeInput.focus()
      }
    })
  }

  // Barcode input validation
  if (barcodeInput) {
    barcodeInput.addEventListener("input", function () {
      const value = this.value.replace(/\D/g, "") // Remove non-digits
      this.value = value

      // Validate length
      const isValid = value.length >= 8 && value.length <= 14
      this.classList.toggle("is-valid", isValid && value.length > 0)
      this.classList.toggle("is-invalid", !isValid && value.length > 0)
    })
  }
}

function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    validateAndPreviewFile(file)
  }
}

function handleDragOver(event) {
  event.preventDefault()
  event.currentTarget.classList.add("dragover")
}

function handleDragLeave(event) {
  event.preventDefault()
  event.currentTarget.classList.remove("dragover")
}

function handleFileDrop(event) {
  event.preventDefault()
  event.currentTarget.classList.remove("dragover")

  const files = event.dataTransfer.files
  if (files.length > 0) {
    const file = files[0]
    document.getElementById("image-input").files = files
    validateAndPreviewFile(file)
  }
}

function validateAndPreviewFile(file) {
  // Validate file type
  const validTypes = ["image/jpeg", "image/jpg", "image/png", "image/webp"]
  if (!validTypes.includes(file.type)) {
    showError("Please select a valid image file (JPEG, PNG, or WebP).")
    return
  }

  // Validate file size (max 10MB)
  const maxSize = 10 * 1024 * 1024
  if (file.size > maxSize) {
    showError("File size must be less than 10MB.")
    return
  }

  // Show preview
  showImagePreview(file)

  // Enable submit button
  const submitBtn = document.getElementById("scan-submit-btn")
  if (submitBtn) {
    submitBtn.disabled = false
    submitBtn.textContent = "Scan Barcode"
  }
}

function showImagePreview(file) {
  const previewContainer = document.getElementById("preview-container")
  const previewImage = document.getElementById("preview-image")

  if (!previewContainer || !previewImage) return

  const reader = new FileReader()
  reader.onload = (e) => {
    previewImage.src = e.target.result
    previewContainer.style.display = "block"

    // Add fade-in animation
    previewContainer.classList.add("fade-in")
  }
  reader.readAsDataURL(file)
}

function handleScanSubmit(event) {
  const submitBtn = event.target.querySelector('button[type="submit"]')
  const fileInput = document.getElementById("image-input")

  if (!fileInput.files.length) {
    event.preventDefault()
    showError("Please select an image to scan.")
    return
  }

  // Show loading state
  if (submitBtn) {
    submitBtn.disabled = true
    submitBtn.innerHTML = `
            <span class="loading-spinner me-2"></span>
            Scanning...
        `
  }

  // Show scanning tips
  showScanningTips()
}

function showScanningTips() {
  const tipsContainer = document.getElementById("scanning-tips")
  if (tipsContainer) {
    tipsContainer.style.display = "block"
    tipsContainer.classList.add("fade-in")
  }
}

function showError(message) {
  const errorContainer = document.getElementById("error-container")
  if (errorContainer) {
    errorContainer.innerHTML = `
            <div class="alert alert-danger alert-dismissible fade show">
                <i class="bi bi-exclamation-triangle me-2"></i>
                ${message}
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `
    errorContainer.scrollIntoView({ behavior: "smooth", block: "nearest" })
  } else {
    // Fallback to notification
    if (window.FoodScanner) {
      window.FoodScanner.showNotification(message, "danger")
    }
  }
}

// Camera functionality (if supported)
function initializeCamera() {
  const cameraBtn = document.getElementById("camera-btn")
  const videoElement = document.getElementById("camera-video")
  const captureBtn = document.getElementById("capture-btn")

  if (!cameraBtn || !videoElement || !captureBtn) return

  let stream = null

  cameraBtn.addEventListener("click", async function () {
    try {
      stream = await navigator.mediaDevices.getUserMedia({
        video: {
          facingMode: "environment", // Use back camera if available
        },
      })
      videoElement.srcObject = stream
      videoElement.style.display = "block"
      captureBtn.style.display = "block"
      this.style.display = "none"
    } catch (error) {
      console.error("Error accessing camera:", error)
      showError("Unable to access camera. Please use file upload instead.")
    }
  })

  captureBtn.addEventListener("click", () => {
    const canvas = document.createElement("canvas")
    const context = canvas.getContext("2d")

    canvas.width = videoElement.videoWidth
    canvas.height = videoElement.videoHeight
    context.drawImage(videoElement, 0, 0)

    // Convert to blob and create file
    canvas.toBlob(
      (blob) => {
        const file = new File([blob], "camera-capture.jpg", { type: "image/jpeg" })

        // Create FileList-like object
        const dt = new DataTransfer()
        dt.items.add(file)
        document.getElementById("image-input").files = dt.files

        validateAndPreviewFile(file)

        // Stop camera
        if (stream) {
          stream.getTracks().forEach((track) => track.stop())
        }
        videoElement.style.display = "none"
        captureBtn.style.display = "none"
        cameraBtn.style.display = "block"
      },
      "image/jpeg",
      0.8,
    )
  })
}

// Initialize camera if supported
if (navigator.mediaDevices && navigator.mediaDevices.getUserMedia) {
  document.addEventListener("DOMContentLoaded", initializeCamera)
}

// Barcode format validation
function validateBarcode(barcode) {
  // Remove any non-digit characters
  const cleaned = barcode.replace(/\D/g, "")

  // Check length
  if (cleaned.length < 8 || cleaned.length > 14) {
    return false
  }

  // Basic checksum validation for common formats
  if (cleaned.length === 13) {
    return validateEAN13(cleaned)
  } else if (cleaned.length === 12) {
    return validateUPC(cleaned)
  }

  // For other lengths, just check if it's all digits
  return /^\d+$/.test(cleaned)
}

function validateEAN13(barcode) {
  if (barcode.length !== 13) return false

  let sum = 0
  for (let i = 0; i < 12; i++) {
    const digit = Number.parseInt(barcode[i])
    sum += i % 2 === 0 ? digit : digit * 3
  }

  const checkDigit = (10 - (sum % 10)) % 10
  return checkDigit === Number.parseInt(barcode[12])
}

function validateUPC(barcode) {
  if (barcode.length !== 12) return false

  let sum = 0
  for (let i = 0; i < 11; i++) {
    const digit = Number.parseInt(barcode[i])
    sum += i % 2 === 0 ? digit * 3 : digit
  }

  const checkDigit = (10 - (sum % 10)) % 10
  return checkDigit === Number.parseInt(barcode[11])
}

// Export scanner functions
window.Scanner = {
  validateBarcode,
  validateEAN13,
  validateUPC,
  showError,
}
