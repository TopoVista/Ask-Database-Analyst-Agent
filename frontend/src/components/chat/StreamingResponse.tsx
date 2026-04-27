"use client";

export function StreamingResponse({ text }: { text: string }) {
  return <p className="whitespace-pre-wrap text-sm leading-6 text-fg/90">{text}</p>;
}

