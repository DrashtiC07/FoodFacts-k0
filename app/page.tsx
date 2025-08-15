"use client"

import { useState } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Search, Scan } from "lucide-react"
import { useRouter } from "next/navigation"

// Mock product data - replace with actual API calls
const mockProducts = [
  {
    id: "1",
    barcode: "3017620422003",
    name: "Nutella",
    brand: "Ferrero",
    image: "/placeholder.svg?height=200&width=200",
    healthScore: 65,
    category: "Spreads",
    ingredients: ["Sugar", "Palm Oil", "Hazelnuts", "Cocoa"],
    nutritionGrade: "D",
  },
  {
    id: "2",
    barcode: "8000500037560",
    name: "Barilla Pasta",
    brand: "Barilla",
    image: "/placeholder.svg?height=200&width=200",
    healthScore: 78,
    category: "Pasta",
    ingredients: ["Durum Wheat", "Water"],
    nutritionGrade: "B",
  },
  {
    id: "3",
    barcode: "4902430735296",
    name: "Coca Cola",
    brand: "Coca-Cola",
    image: "/placeholder.svg?height=200&width=200",
    healthScore: 45,
    category: "Beverages",
    ingredients: ["Water", "Sugar", "Carbon Dioxide", "Caramel Color"],
    nutritionGrade: "E",
  },
]

export default function HomePage() {
  const [products, setProducts] = useState(mockProducts)
  const [searchTerm, setSearchTerm] = useState("")
  const router = useRouter()

  const filteredProducts = products.filter(
    (product) =>
      product.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      product.brand.toLowerCase().includes(searchTerm.toLowerCase()),
  )

  const handleProductClick = (productId: string) => {
    console.log("[v0] Navigating to product:", productId)
    router.push(`/product/${productId}`)
  }

  const getGradeColor = (grade: string) => {
    switch (grade) {
      case "A":
        return "bg-green-500"
      case "B":
        return "bg-lime-500"
      case "C":
        return "bg-yellow-500"
      case "D":
        return "bg-orange-500"
      case "E":
        return "bg-red-500"
      default:
        return "bg-gray-500"
    }
  }

  return (
    <div className="min-h-screen bg-background">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="container mx-auto px-4 py-6">
          <h1 className="text-3xl font-bold text-foreground mb-4">Food Facts Scanner</h1>

          {/* Search Bar */}
          <div className="flex gap-4 max-w-2xl">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground h-4 w-4" />
              <Input
                placeholder="Search products..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
              />
            </div>
            <Button variant="outline" className="flex items-center gap-2 bg-transparent">
              <Scan className="h-4 w-4" />
              Scan Barcode
            </Button>
          </div>
        </div>
      </header>

      {/* Products Grid */}
      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6">
          {filteredProducts.map((product) => (
            <Card
              key={product.id}
              className="cursor-pointer hover:shadow-lg transition-shadow duration-200"
              onClick={() => handleProductClick(product.id)}
            >
              <CardHeader className="pb-3">
                <div className="aspect-square relative mb-3">
                  <img
                    src={product.image || "/placeholder.svg"}
                    alt={product.name}
                    className="w-full h-full object-cover rounded-md"
                  />
                </div>
                <CardTitle className="text-lg line-clamp-2">{product.name}</CardTitle>
                <p className="text-sm text-muted-foreground">{product.brand}</p>
              </CardHeader>

              <CardContent className="pt-0">
                <div className="flex items-center justify-between mb-3">
                  <Badge variant="secondary">{product.category}</Badge>
                  <div className="flex items-center gap-2">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center text-white text-xs font-bold ${getGradeColor(product.nutritionGrade)}`}
                    >
                      {product.nutritionGrade}
                    </div>
                  </div>
                </div>

                <div className="space-y-2">
                  <div className="flex justify-between text-sm">
                    <span className="text-muted-foreground">Health Score:</span>
                    <span className="font-medium">{product.healthScore}/100</span>
                  </div>

                  <div className="w-full bg-muted rounded-full h-2">
                    <div
                      className="bg-primary h-2 rounded-full transition-all duration-300"
                      style={{ width: `${product.healthScore}%` }}
                    />
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>

        {filteredProducts.length === 0 && (
          <div className="text-center py-12">
            <p className="text-muted-foreground">No products found matching your search.</p>
          </div>
        )}
      </main>
    </div>
  )
}
