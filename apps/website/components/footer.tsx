import { GITHUB_REPO_URL, TRYMAGIC_URL } from "@/constants/config";
import Logo, { TrymagicLogo } from "./logo";
import { Info } from "lucide-react";

export default function Footer() {
  const currentYear = new Date().getFullYear();
  return (
   <>
    <footer className="w-full border-t mt-8 px-6 py-12 bg-[#fafafa] dark:bg-[#0d0d0d]">
      <div className="max-w-6xl mx-auto flex flex-col md:flex-row justify-between items-center gap-6">
        <Logo />

        <p className="text-sm text-[#666] dark:text-[#aaa] text-center md:text-left">
          © {currentYear} Chainless - Built for faster, more powerful, and simpler ai flows
        </p>

        <div className="flex max-sm:flex-col items-center gap-6">
          <div className="flex space-x-4">
            <a
              href="/docs"
              className="text-sm hover:underline text-[#444] dark:text-[#ccc]"
            >
              Docs
            </a>
            <a
              href={GITHUB_REPO_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="text-sm hover:underline text-[#444] dark:text-[#ccc]"
            >
              GitHub
            </a>
          </div>

          <a
            href={TRYMAGIC_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-3 group text-[#838383] dark:text-[#6e6e6e] font-semibold text-xs"
            title="Trymagic Open Source Projects"
          >
            <span>by</span>
            <TrymagicLogo className="group-hover:scale-105 active:scale-100 transition-all" />
          </a>
        </div>
      </div>

      <p className="text-xs text-center text-[#999] dark:text-[#666] mt-6 italic select-none">
        ❤️ Made with love - Chainless & Trymagic
      </p>
    </footer>
    <div className="w-full flex  items-center justify-center gap-1.5 bg-[#e8e8e8] dark:bg-[#292929] text-sm p-2 text-[#515151] dark:text-[#b8b8b8]">
      <Info size={15}/> <span>The docs in this project were written by a taskflow agent developed with the chainless library.</span>
    </div>
   
   </>
  );
}
