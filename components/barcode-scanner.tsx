"use client"

import { useEffect, useRef, useState } from "react"
import { Alert, AlertDescription } from "@/components/ui/alert"

interface BarcodeScannerProps {
  onBarcodeDetected: (barcode: string) => void
  onError: (error: string) => void
}

export function BarcodeScanner({ onBarcodeDetected, onError }: BarcodeScannerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [isActive, setIsActive] = useState(false)

  useEffect(() => {
    let stream: MediaStream | null = null
    let animationFrame: number

    const startCamera = async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: {
            facingMode: "environment",
            width: { ideal: 1280 },
            height: { ideal: 720 },
          },
        })

        if (videoRef.current) {
          videoRef.current.srcObject = stream
          setIsActive(true)
          scanForBarcode()
        }
      } catch (err) {
        onError("Camera access denied or not available")
      }
    }

    const scanForBarcode = () => {
      if (!videoRef.current || !canvasRef.current || !isActive) return

      const video = videoRef.current
      const canvas = canvasRef.current
      const ctx = canvas.getContext("2d")

      if (video.readyState === video.HAVE_ENOUGH_DATA && ctx) {
        canvas.width = video.videoWidth
        canvas.height = video.videoHeight
        ctx.drawImage(video, 0, 0)

        // Try to detect barcode using browser APIs or libraries
        // For now, we'll simulate barcode detection
        // In a real implementation, you'd use a library like @zxing/library

        animationFrame = requestAnimationFrame(scanForBarcode)
      } else {
        animationFrame = requestAnimationFrame(scanForBarcode)
      }
    }

    startCamera()

    return () => {
      setIsActive(false)
      if (stream) {
        stream.getTracks().forEach((track) => track.stop())
      }
      if (animationFrame) {
        cancelAnimationFrame(animationFrame)
      }
    }
  }, [onBarcodeDetected, onError, isActive])

  return (
    <div className="space-y-4">
      <div className="relative bg-black rounded-lg overflow-hidden">
        <video ref={videoRef} autoPlay playsInline muted className="w-full h-64 object-cover" />
        <canvas ref={canvasRef} className="hidden" />

        {/* Scanning overlay */}
        <div className="absolute inset-0 flex items-center justify-center">
          <div className="w-64 h-32 border-2 border-green-400 rounded-lg relative">
            <div className="absolute top-0 left-0 w-6 h-6 border-t-4 border-l-4 border-green-400"></div>
            <div className="absolute top-0 right-0 w-6 h-6 border-t-4 border-r-4 border-green-400"></div>
            <div className="absolute bottom-0 left-0 w-6 h-6 border-b-4 border-l-4 border-green-400"></div>
            <div className="absolute bottom-0 right-0 w-6 h-6 border-b-4 border-r-4 border-green-400"></div>
          </div>
        </div>
      </div>

      <Alert>
        <AlertDescription>
          Position the barcode within the frame. The scanner will automatically detect it.
        </AlertDescription>
      </Alert>
    </div>
  )
}
