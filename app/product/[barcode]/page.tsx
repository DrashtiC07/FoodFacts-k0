import { notFound } from "next/navigation"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Badge } from "@/components/ui/badge"
import { Progress } from "@/components/ui/progress"
import { Button } from "@/components/ui/button"
import { ArrowLeft, Heart, Share2, AlertTriangle } from "lucide-react"
import Link from "next/link"
import Image from "next/image"

interface ProductPageProps {
  params: {
    barcode: string
  }
}

async function getProductData(barcode: string) {
  try {
    const response = await fetch(`https://world.openfoodfacts.org/api/v2/product/${barcode}.json`, {
      headers: {
        "User-Agent": "FoodScanner/2.0 (Next.js App)",
      },
    })

    const data = await response.json()

    if (data.status === 1) {
      return data.product
    }

    return null
  } catch (error) {
    console.error("Error fetching product:", error)
    return null
  }
}

function getHealthScore(nutriments: any): number {
  let score = 100

  // Deduct points for high values
  if (nutriments.fat_100g > 20) score -= 15
  if (nutriments.saturated_fat_100g > 5) score -= 10
  if (nutriments.sugars_100g > 15) score -= 20
  if (nutriments.salt_100g > 1.5) score -= 15
  if (nutriments.sodium_100g > 600) score -= 10

  // Add points for good values
  if (nutriments.fiber_100g > 3) score += 10
  if (nutriments.proteins_100g > 10) score += 5

  return Math.max(0, Math.min(100, score))
}

function getScoreColor(score: number): string {
  if (score >= 80) return "text-green-600"
  if (score >= 60) return "text-yellow-600"
  return "text-red-600"
}

export default async function ProductPage({ params }: ProductPageProps) {
  const product = await getProductData(params.barcode)

  if (!product) {
    notFound()
  }

  const healthScore = getHealthScore(product.nutriments || {})
  const nutriments = product.nutriments || {}

  return (
    <div className="min-h-screen bg-gradient-to-br from-green-50 to-blue-50 dark:from-gray-900 dark:to-gray-800">
      {/* Header */}
      <header className="border-b bg-white/80 dark:bg-gray-900/80 backdrop-blur-sm sticky top-0 z-50">
        <div className="container mx-auto px-4 py-4 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <Link href="/">
              <Button variant="ghost" size="icon">
                <ArrowLeft className="w-5 h-5" />
              </Button>
            </Link>
            <h1 className="text-xl font-bold text-gray-900 dark:text-white">Product Details</h1>
          </div>

          <div className="flex items-center space-x-2">
            <Button variant="ghost" size="icon">
              <Heart className="w-5 h-5" />
            </Button>
            <Button variant="ghost" size="icon">
              <Share2 className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="container mx-auto px-4 py-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Product Header */}
          <Card>
            <CardContent className="p-6">
              <div className="grid gap-6 md:grid-cols-2">
                <div className="space-y-4">
                  <div>
                    <h2 className="text-2xl font-bold text-gray-900 dark:text-white">
                      {product.product_name || `Product ${params.barcode}`}
                    </h2>
                    {product.brands && <p className="text-lg text-gray-600 dark:text-gray-400">{product.brands}</p>}
                  </div>

                  <div className="flex items-center space-x-4">
                    <div className="text-center">
                      <div className={`text-3xl font-bold ${getScoreColor(healthScore)}`}>{healthScore}</div>
                      <div className="text-sm text-gray-600 dark:text-gray-400">Health Score</div>
                    </div>

                    {product.ecoscore_grade && (
                      <div className="text-center">
                        <div className="text-2xl font-bold text-green-600">{product.ecoscore_grade.toUpperCase()}</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">Eco Score</div>
                      </div>
                    )}

                    {product.nova_group && (
                      <div className="text-center">
                        <div className="text-2xl font-bold text-blue-600">{product.nova_group}</div>
                        <div className="text-sm text-gray-600 dark:text-gray-400">NOVA Group</div>
                      </div>
                    )}
                  </div>
                </div>

                <div className="flex justify-center">
                  {product.image_url ? (
                    <Image
                      src={product.image_url || "/placeholder.svg"}
                      alt={product.product_name || "Product image"}
                      width={200}
                      height={200}
                      className="rounded-lg object-cover"
                    />
                  ) : (
                    <div className="w-48 h-48 bg-gray-200 dark:bg-gray-700 rounded-lg flex items-center justify-center">
                      <span className="text-gray-500">No Image</span>
                    </div>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>

          {/* Nutrition Facts */}
          <Card>
            <CardHeader>
              <CardTitle>Nutrition Facts (per 100g)</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                {nutriments.energy_kcal_100g && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Energy</span>
                      <span className="font-semibold">{nutriments.energy_kcal_100g} kcal</span>
                    </div>
                  </div>
                )}

                {nutriments.fat_100g !== undefined && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Fat</span>
                      <span className="font-semibold">{nutriments.fat_100g}g</span>
                    </div>
                    <Progress value={Math.min(100, (nutriments.fat_100g / 30) * 100)} className="h-2" />
                  </div>
                )}

                {nutriments.saturated_fat_100g !== undefined && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Saturated Fat</span>
                      <span className="font-semibold">{nutriments.saturated_fat_100g}g</span>
                    </div>
                    <Progress value={Math.min(100, (nutriments.saturated_fat_100g / 10) * 100)} className="h-2" />
                  </div>
                )}

                {nutriments.carbohydrates_100g !== undefined && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Carbohydrates</span>
                      <span className="font-semibold">{nutriments.carbohydrates_100g}g</span>
                    </div>
                    <Progress value={Math.min(100, (nutriments.carbohydrates_100g / 50) * 100)} className="h-2" />
                  </div>
                )}

                {nutriments.sugars_100g !== undefined && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Sugars</span>
                      <span className="font-semibold">{nutriments.sugars_100g}g</span>
                    </div>
                    <Progress value={Math.min(100, (nutriments.sugars_100g / 25) * 100)} className="h-2" />
                  </div>
                )}

                {nutriments.proteins_100g !== undefined && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Protein</span>
                      <span className="font-semibold">{nutriments.proteins_100g}g</span>
                    </div>
                    <Progress value={Math.min(100, (nutriments.proteins_100g / 20) * 100)} className="h-2" />
                  </div>
                )}

                {nutriments.salt_100g !== undefined && (
                  <div className="space-y-2">
                    <div className="flex justify-between">
                      <span>Salt</span>
                      <span className="font-semibold">{nutriments.salt_100g}g</span>
                    </div>
                    <Progress value={Math.min(100, (nutriments.salt_100g / 2) * 100)} className="h-2" />
                  </div>
                )}
              </div>
            </CardContent>
          </Card>

          {/* Ingredients */}
          {product.ingredients_text && (
            <Card>
              <CardHeader>
                <CardTitle>Ingredients</CardTitle>
              </CardHeader>
              <CardContent>
                <p className="text-gray-700 dark:text-gray-300 leading-relaxed">{product.ingredients_text}</p>
              </CardContent>
            </Card>
          )}

          {/* Allergens & Labels */}
          <div className="grid gap-6 md:grid-cols-2">
            {product.allergens_tags && product.allergens_tags.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle className="flex items-center space-x-2">
                    <AlertTriangle className="w-5 h-5 text-red-500" />
                    <span>Allergens</span>
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {product.allergens_tags.map((allergen: string, index: number) => (
                      <Badge key={index} variant="destructive">
                        {allergen.replace("en:", "").replace(/-/g, " ")}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}

            {product.labels_tags && product.labels_tags.length > 0 && (
              <Card>
                <CardHeader>
                  <CardTitle>Labels</CardTitle>
                </CardHeader>
                <CardContent>
                  <div className="flex flex-wrap gap-2">
                    {product.labels_tags.slice(0, 10).map((label: string, index: number) => (
                      <Badge key={index} variant="secondary">
                        {label.replace("en:", "").replace(/-/g, " ")}
                      </Badge>
                    ))}
                  </div>
                </CardContent>
              </Card>
            )}
          </div>

          {/* Product Info */}
          <Card>
            <CardHeader>
              <CardTitle>Product Information</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid gap-4 md:grid-cols-2">
                <div>
                  <span className="font-semibold">Barcode:</span>
                  <span className="ml-2">{params.barcode}</span>
                </div>
                {product.categories && (
                  <div>
                    <span className="font-semibold">Categories:</span>
                    <span className="ml-2">{product.categories}</span>
                  </div>
                )}
                {product.countries && (
                  <div>
                    <span className="font-semibold">Countries:</span>
                    <span className="ml-2">{product.countries}</span>
                  </div>
                )}
                <div>
                  <span className="font-semibold">Data Source:</span>
                  <span className="ml-2">Open Food Facts</span>
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </main>
    </div>
  )
}
