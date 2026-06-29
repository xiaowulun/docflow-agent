"use client";

interface AstronautProps {
  size?: number;
  className?: string;
  animated?: boolean;
}

export default function Astronaut({ size = 36, className = "", animated = true }: AstronautProps) {
  return (
    <div
      className={`flex items-center justify-center overflow-hidden rounded-xl bg-gradient-to-b from-zinc-100 to-zinc-300 shadow-md ring-1 ring-zinc-200/60 ${className}`}
      style={{ width: size, height: size }}
    >
      <svg viewBox="0 0 40 40" className="h-full w-full" xmlns="http://www.w3.org/2000/svg">
        <ellipse cx="20" cy="35" rx="10" ry="5" fill="#d4d4d8" />
        <path d="M10 28 Q10 23 20 23 Q30 23 30 28 L30 34 Q30 37 20 37 Q10 37 10 34 Z" fill="#e4e4e7" />
        <rect x="15" y="28" width="10" height="2.5" rx="1" fill="#a1a1aa" opacity="0.3" />
        <path d="M8 20 Q8 13 20 13 Q32 13 32 20 L32 22 L8 22 Z" fill="#f4f4f5" />
        <path d="M7 20 Q7 11 20 11 Q33 11 33 20 L33 22 L31 22 L31 20 Q31 13 20 13 Q9 13 9 20 L9 22 L7 22 Z" fill="#a1a1aa" />
        <ellipse cx="20" cy="17.5" rx="11" ry="8.5" fill="#18181b" />
        <ellipse cx="15" cy="14" rx="3" ry="3.5" fill="white" opacity="0.08" />
        <ellipse cx="26" cy="19" rx="1.5" ry="2" fill="white" opacity="0.05" />
        <circle cx="16" cy="17" r="1.6" fill="#34d399" className={animated ? "eye-blink" : ""} />
        <circle cx="24" cy="17" r="1.6" fill="#34d399" className={animated ? "eye-blink" : ""} />
        <rect x="4" y="15" width="4" height="7" rx="1.5" fill="#71717a" />
        <rect x="3" y="17" width="1.5" height="3" rx="0.75" fill="#52525b" />
        <rect x="32" y="15" width="4" height="7" rx="1.5" fill="#71717a" />
        <rect x="35.5" y="17" width="1.5" height="3" rx="0.75" fill="#52525b" />
        <line x1="20" y1="11" x2="20" y2="6" stroke="#a1a1aa" strokeWidth="1" strokeLinecap="round" />
        <circle cx="20" cy="5" r="1" fill="#71717a" />
      </svg>
    </div>
  );
}
