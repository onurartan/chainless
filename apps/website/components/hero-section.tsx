"use client";

import React, { useState, useEffect, useRef } from "react";
import Link from "next/link";
import { ArrowRight, Github } from "lucide-react";
import Container from "./container";
import { GITHUB_REPO_URL } from "@/constants/config";
import { motion } from "motion/react";

const GRID_SIZE = 14;

const HeroSection = () => {
  const [mouse, setMouse] = useState({ x: 0, y: 0 });
  const gridRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const move = (e: MouseEvent) => {
      setMouse({ x: e.clientX, y: e.clientY });
    };
    window.addEventListener("mousemove", move);
    return () => window.removeEventListener("mousemove", move);
  }, []);

  return (
    <Container
      as="section"
      className="relative overflow-hidden border border-[#e5e5e5] dark:border-[#1e1e1e] rounded-b-3xl flex items-center justify-center mt-4 px-6 py-1 text-center"
    >
      {/* === INTERACTIVE GRID === */}
      <div
        ref={gridRef}
        className="absolute inset-0 pointer-events-none z-0  grid grid-cols-17  opacity-[0.35]"
      >
        {[...Array(GRID_SIZE * GRID_SIZE)].map((_, i) => {
          const col = i % GRID_SIZE;
          const row = Math.floor(i / GRID_SIZE);

          return (
            <GridCell
              key={i}
              col={col}
              row={row}
              mouse={mouse}
              total={GRID_SIZE}
              gridRef={gridRef}
            />
          );
        })}
      </div>

      {/* === FOREGROUND === */}
      <div className="relative z-10 max-w-4xl mx-auto flex flex-col items-center">
        <h1 className="text-4xl sm:text-5xl md:text-6xl font-extrabold leading-tight tracking-tight mb-6">

         Build&nbsp;
           <span className="dark:bg-linear-to-r dark:from-[#F9E1FF] dark:via-[#B08EFF] dark:to-[#00C2FF] dark:bg-clip-text dark:text-transparent">
             AI taskflows
          </span>&nbsp;that scale with your ideas.
        </h1>

        <p className="text-gray-400 text-lg sm:text-xl max-w-2xl mb-10">
         Design agents, connect tools, and orchestrate taskflows in Python - predictable, composable, and fully in your control.
        </p>

        <div className="flex flex-wrap justify-center gap-4">
          <Link
            href="/docs"
            className="flex items-center gap-2 bg-black dark:bg-white text-white dark:text-black font-semibold px-7 py-3 rounded-full  active:scale-95 transition-all hover:opacity-75 hover:scale-105"
          >
            Get Started
            <ArrowRight size={18} />
          </Link>

          <a
            href={GITHUB_REPO_URL}
            target="_blank"
            rel="noopener noreferrer"
            className="flex items-center gap-2 border border-[#6a6a6a] dark:border-white/35 text-black dark:text-gray-200 px-7 py-3 rounded-full font-semibold hover:bg-black/5 dark:hover:bg-white/10 transition-all active:scale-95"
          >
            <Github size={20} />
            View on GitHub
          </a>
        </div>
      </div>
    </Container>
  );
};

export default HeroSection;


const GridCell = ({
  col,
  row,
  mouse,
  total,
  gridRef,
}: {
  col: number;
  row: number;
  mouse: { x: number; y: number };
  total: number;
  gridRef: React.RefObject<HTMLDivElement | null>;
}) => {
  const isDark =
    typeof window !== "undefined" &&
    getComputedStyle(document.documentElement)
      .getPropertyValue("color-scheme")
      .includes("dark");

  const rect = gridRef.current?.getBoundingClientRect();

  // grid container  width/height
  const cellW = rect ? rect.width / total : 75;
  const cellH = rect ? rect.height / total : 75;

  
  const centerX = rect ? rect.left + col * cellW + cellW / 2 : 0;
  const centerY = rect ? rect.top + row * cellH + cellH / 2 : 0;

  const dx = mouse.x - centerX;
  const dy = mouse.y - centerY;
  const dist = Math.sqrt(dx * dx + dy * dy);

  // YAKIN → parlak, UZAK → sönük
  const intensity = Math.max(0, 1 - dist / 220);

  const bgBaseColor = isDark ? "#000" : "#efefef";

  const gradient = isDark
    ? "linear-gradient(135deg, #F9E1FF55, #00C2FF66)" // dark
    : "linear-gradient(135deg, #E2C3FFAA, #00A8FFCC)"; // light

  return (
    <motion.div
      className="border border-[rgb(137,137,137)] w-[75px] h-[75px] "
      animate={{
        opacity: 0.4 + intensity * 0.9,
        borderColor: intensity > 0.4 ? "" : "rgba(175,175,175,0.99)",
      }}
      style={{
        background: intensity > 0.4 ? gradient : bgBaseColor,
        transition: "background 0.12s, opacity 0.12s",
      }}
      transition={{ duration: 0.12 }}
    />
  );
};
