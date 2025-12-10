"use client";
import Footer from "@/components/footer";
import HeroSection from "@/components/hero-section";
import WhyDevelopersLove from "@/components/WhyDevelopersLove";

export default function HomePage() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-[#fff] dark:bg-[#0d0d0d]  text-center text-[#111] dark:text-[#f4f4f4]">
      <HeroSection />
      <WhyDevelopersLove />
      <Footer />
    </main>
  );
}
