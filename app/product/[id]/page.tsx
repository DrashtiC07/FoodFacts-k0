"use client"

import { useState, useEffect } from "react"
import { useParams, useRouter } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Heart, Share2, Star } from "lucide-react"
import { Separator } from "@/components/ui/separator"

// Mock product data - replace with actual API calls
const mockProductDetails = {
  "1": {
    id: "1",
    barcode: "3017620422003",
    name: "Nutella",
    brand: "Ferrero",
    image: "/placeholder.svg?height=400&width=400",
    healthScore: 65,
    category: "Spreads",
    ingredients: [
      "Sugar",
      "Palm Oil",
      "Hazelnuts (13%)",
      "Cocoa (7.4%)",
      "Skimmed Milk Powder (6.6%)",
      "Whey Powder",
      "Lecithins",
      "Vanillin",
    ],
    nutritionGrade: "D",
    nutrition: {
      energy: "2252 kJ / 539 kcal",
      fat: "30.9g",
      saturatedFat: "10.6g",
      carbohydrates: "57.5g",
      sugars: "56.3g",
      fiber: "0g",
      proteins: "6.3g",
      salt: "0.107g",
    },
    allergens: ["Milk", "Nuts", "May contain gluten"],
    description:
      "Nutella is a sweetened hazelnut cocoa spread. Nutella is manufactured by the Italian company Ferrero and was first introduced in 1964.",
    rating: 4.2,
    reviews: 1247,
  },
}

export default function ProductDetailPage() {
  const params = useParams()
  const router = useRouter()
  const productId = params.id as string

  const [product, setProduct] = useState(mockProductDetails[productId as keyof typeof mockProductDetails])
  const [isFavorite, setIsFavorite] = useState(false)

  useEffect(() => {
    console.log("[v0] Loading product details for ID:", productId)
    // In a real app, you would fetch product details from an API here
    if (!product) {
      console.log("[v0] Product not found, redirecting to home")
      router.push("/")
    }
  }, [productId, product, router])

  if (!product) {
    return (
      <div className="min-h-screen bg-background flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-2xl font-bold mb-4">Product Not Found</h2>
          <Button onClick={() => router.push("/")}>
            <ArrowLeft className="h-4 w-4 mr-2" />
            Back to Products
          </Button>
        </div>
      </div>
    )
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
        <div className="container mx-auto px-4 py-4">
          <div className="flex items-center gap-4">
            <Button variant="ghost" size="sm" onClick={() => router.push("/")} className="flex items-center gap-2">
              <ArrowLeft className="h-4 w-4" />
              Back
            </Button>
            <h1 className="text-2xl font-bold">Product Details</h1>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Product Image */}
          <div className="space-y-4">
            <div className="aspect-square relative">
              <img
                src={product.image || "/placeholder.svg"}
                alt={product.name}
                className="w-full h-full object-cover rounded-lg"
              />
            </div>
          </div>

          {/* Product Info */}
          <div className="space-y-6">
            <div>
              <div className="flex items-start justify-between mb-2">
                <div>
                  <h1 className="text-3xl font-bold">{product.name}</h1>
                  <p className="text-xl text-muted-foreground">{product.brand}</p>
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" size="sm" onClick={() => setIsFavorite(!isFavorite)}>
                    <Heart className={`h-4 w-4 ${isFavorite ? "fill-red-500 text-red-500" : ""}`} />
                  </Button>
                  <Button variant="outline" size="sm">
                    <Share2 className="h-4 w-4" />
                  </Button>
                </div>
              </div>

              <div className="flex items-center gap-4 mb-4">
                <Badge variant="secondary">{product.category}</Badge>
                <div
                  className={`w-8 h-8 rounded-full flex items-center justify-center text-white font-bold ${getGradeColor(product.nutritionGrade)}`}
                >
                  {product.nutritionGrade}
                </div>
                <div className="flex items-center gap-1">
                  <Star className="h-4 w-4 fill-yellow-400 text-yellow-400" />
                  <span className="font-medium">{product.rating}</span>
                  <span className="text-muted-foreground">({product.reviews} reviews)</span>
                </div>
              </div>

              <p className="text-muted-foreground mb-4">{product.description}</p>

              <div className="space-y-2">
                <div className="flex justify-between text-sm">
                  <span className="text-muted-foreground">Health Score:</span>
                  <span className="font-medium">{product.healthScore}/100</span>
                </div>
                <div className="w-full bg-muted rounded-full h-3">
                  <div
                    className="bg-primary h-3 rounded-full transition-all duration-300"
                    style={{ width: `${product.healthScore}%` }}
                  />
                </div>
              </div>
            </div>

            <Separator />

            {/* Nutrition Facts */}
            <Card>
              <CardHeader>
                <CardTitle>Nutrition Facts (per 100g)</CardTitle>
              </CardHeader>
              <CardContent className="space-y-3">
                {Object.entries(product.nutrition).map(([key, value]) => (
                  <div key={key} className="flex justify-between">
                    <span className="capitalize text-muted-foreground">
                      {key.replace(/([A-Z])/g, " $1").toLowerCase()}:
                    </span>
                    <span className="font-medium">{value}</span>
                  </div>
                ))}
              </CardContent>
            </Card>

            {/* Ingredients */}
            <Card>
              <CardHeader>
                <CardTitle>Ingredients</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-sm">{product.ingredients.join(", ")}</p>
              </CardContent>
            </Card>

            {/* Allergens */}
            <Card>
              <CardHeader>
                <CardTitle>Allergens</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex flex-wrap gap-2">
                  {product.allergens.map((allergen, index) => (
                    <Badge key={index} variant="destructive">
                      {allergen}
                    </Badge>
                  ))}
                </div>
              </CardContent>
            </Card>
          </div>
        </div>
      </main>
    </div>
  )
}
