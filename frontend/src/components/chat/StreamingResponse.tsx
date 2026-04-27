"use client";

import { RichTextMessage } from "./RichTextMessage";

export function StreamingResponse({ text }: { text: string }) {
  return <RichTextMessage text={text} />;
}
