"use client"

import type React from "react"

import { useState, useRef, useCallback } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Alert, AlertDescription } from "@/components/ui/alert"
import { Camera, Upload, ArrowLeft, Zap } from "lucide-react"
import Link from "next/link"
import { BarcodeScanner } from "@/components/barcode-scanner"

export default function ScanPage() {
  const [isScanning, setIsScanning] = useState(false)
  const [error, setError] = useState("")
  const [isProcessing, setIsProcessing] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const handleBarcodeDetected = useCallback(async (barcode: string) => {
    setIsProcessing(true)
    setError("")

    try {
      // Redirect to product page
      window.location.href = `/product/${barcode}`
    } catch (err) {
      setError("Failed to process barcode. Please try again.")
      setIsProcessing(false)
    }
  }, [])

  const handleFileUpload = async (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return

    setIsProcessing(true)
    setError("")

    try {
      // Create form data and send to API
      const formData = new FormData()
      formData.append("image", file)

      const response = await fetch("/api/scan-image", {
        method: "POST",
        body: formData,
      })

      const result = await response.json()

      if (result.success && result.barcode) {
        window.location.href = `/product/${result.barcode}`
      } else {
        setError(result.error || "No barcode detected in image. Please try again with a clearer image.")
      }
    } catch (err) {
      setError("Failed to process image. Please try again.")
    } finally {
      setIsProcessing(false)
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm">
        <div className="container mx-auto px-4 py-4 flex items-center space-x-4">
          <Link href="/">
            <Button variant="ghost" size="icon">
              <ArrowLeft className="w-5 h-5" />
            </Button>
          </Link>
          <h1 className="text-xl font-bold text-gray-900 dark:text-white">Scan Product</h1>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-6">
          {error && (
            <Alert variant="destructive">
              <AlertDescription>{error}</AlertDescription>
            </Alert>
          )}

          {/* Camera Scanner */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Camera className="w-5 h-5" />
                <span>Camera Scanner</span>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {!isScanning ? (
                <Button onClick={() => setIsScanning(true)} className="w-full" size="lg" disabled={isProcessing}>
                  <Camera className="w-5 h-5 mr-2" />
                  Start Camera
                </Button>
              ) : (
                <div className="space-y-4">
                  <BarcodeScanner onBarcodeDetected={handleBarcodeDetected} onError={setError} />
                  <Button onClick={() => setIsScanning(false)} variant="outline" className="w-full">
                    Stop Camera
                  </Button>
                </div>
              )}
            </CardContent>
          </Card>

          {/* File Upload */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Upload className="w-5 h-5" />
                <span>Upload Image</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <input ref={fileInputRef} type="file" accept="image/*" onChange={handleFileUpload} className="hidden" />
              <Button
                onClick={() => fileInputRef.current?.click()}
                variant="outline"
                className="w-full"
                size="lg"
                disabled={isProcessing}
              >
                <Upload className="w-5 h-5 mr-2" />
                {isProcessing ? "Processing..." : "Choose Image"}
              </Button>
            </CardContent>
          </Card>

          {/* Tips */}
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center space-x-2">
                <Zap className="w-5 h-5" />
                <span>Scanning Tips</span>
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-2 text-sm text-gray-600 dark:text-gray-400">
                <li>• Ensure the barcode is clearly visible and well-lit</li>
                <li>• Hold the camera steady and at the right distance</li>
                <li>• Clean your camera lens for better results</li>
                <li>• Try different angles if the barcode isn't detected</li>
              </ul>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
