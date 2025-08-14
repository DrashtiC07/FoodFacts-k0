"use client"

import { useState } from "react"
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Badge } from "@/components/ui/badge"
import { Camera, Search, History, User, Moon, Sun } from "lucide-react"
import { useTheme } from "next-themes"
import Link from "next/link"

export default function HomePage() {
  const [manualBarcode, setManualBarcode] = useState("")
  const { theme, setTheme } = useTheme()

  const handleManualScan = () => {
    if (manualBarcode.trim()) {
      window.location.href = `/product/${manualBarcode.trim()}`
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-2">
            <div className="w-8 h-8 bg-green-500 rounded-lg flex items-center justify-center">
              <Search className="w-5 h-5 text-white" />
            </div>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">FoodScanner</h1>
          </div>

          <div className="flex items-center space-x-4">
            <Button variant="ghost" size="icon" onClick={() => setTheme(theme === "dark" ? "light" : "dark")}>
              {theme === "dark" ? <Sun className="w-5 h-5" /> : <Moon className="w-5 h-5" />}
            </Button>
            <Link href="/history">
              <Button variant="ghost" size="icon">
                <History className="w-5 h-5" />
              </Button>
            </Link>
            <Link href="/profile">
              <Button variant="ghost" size="icon">
                <User className="w-5 h-5" />
              </Button>
            </Link>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="container mx-auto px-4 py-8">
        <div className="max-w-2xl mx-auto space-y-8">
          {/* Welcome Section */}
          <div className="text-center space-y-4">
            <h2 className="text-3xl font-bold text-gray-900 dark:text-white">Discover Food Facts</h2>
            <p className="text-lg text-gray-600 dark:text-gray-300">
              Scan barcodes to get detailed nutritional information, ingredients, and health scores
            </p>
          </div>

          {/* Scanning Options */}
          <div className="grid gap-6 md:grid-cols-2">
            {/* Camera Scan */}
            <Card className="hover:shadow-lg transition-shadow">
              <CardHeader className="text-center">
                <div className="w-16 h-16 bg-blue-100 dark:bg-blue-900 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Camera className="w-8 h-8 text-blue-600 dark:text-blue-400" />
                </div>
                <CardTitle>Camera Scan</CardTitle>
                <CardDescription>Use your camera to scan product barcodes</CardDescription>
              </CardHeader>
              <CardContent>
                <Link href="/scan">
                  <Button className="w-full" size="lg">
                    Start Camera Scan
                  </Button>
                </Link>
              </CardContent>
            </Card>

            {/* Manual Entry */}
            <Card className="hover:shadow-lg transition-shadow">
              <CardHeader className="text-center">
                <div className="w-16 h-16 bg-green-100 dark:bg-green-900 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Search className="w-8 h-8 text-green-600 dark:text-green-400" />
                </div>
                <CardTitle>Manual Entry</CardTitle>
                <CardDescription>Enter barcode numbers manually</CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <Input
                  placeholder="Enter barcode (8-14 digits)"
                  value={manualBarcode}
                  onChange={(e) => setManualBarcode(e.target.value.replace(/\D/g, ""))}
                  maxLength={14}
                />
                <Button
                  className="w-full"
                  size="lg"
                  onClick={handleManualScan}
                  disabled={!manualBarcode.trim() || manualBarcode.length < 8}
                >
                  Look Up Product
                </Button>
              </CardContent>
            </Card>
          </div>

          {/* Features */}
          <Card>
            <CardHeader>
              <CardTitle>What You'll Get</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div className="flex items-start space-x-3">
                  <Badge variant="secondary" className="mt-1">
                    ✓
                  </Badge>
                  <div>
                    <h4 className="font-semibold">Nutritional Information</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">
                      Complete nutrition facts and health scores
                    </p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <Badge variant="secondary" className="mt-1">
                    ✓
                  </Badge>
                  <div>
                    <h4 className="font-semibold">Ingredients List</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Full ingredients with allergen detection</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <Badge variant="secondary" className="mt-1">
                    ✓
                  </Badge>
                  <div>
                    <h4 className="font-semibold">Eco Score</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Environmental impact rating</p>
                  </div>
                </div>
                <div className="flex items-start space-x-3">
                  <Badge variant="secondary" className="mt-1">
                    ✓
                  </Badge>
                  <div>
                    <h4 className="font-semibold">Scan History</h4>
                    <p className="text-sm text-gray-600 dark:text-gray-400">Track your scanned products</p>
                  </div>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
