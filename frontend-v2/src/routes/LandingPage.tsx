import { Hero } from '@/components/marketing/Hero'
import { HowItWorks } from '@/components/marketing/HowItWorks'
import { FixtureWalkthrough } from '@/components/marketing/FixtureWalkthrough'
import { Footer } from '@/components/marketing/Footer'

export function LandingPage() {
  return (
    <div className="min-h-svh">
      <Hero />
      <HowItWorks />
      <FixtureWalkthrough />
      <Footer />
    </div>
  )
}
