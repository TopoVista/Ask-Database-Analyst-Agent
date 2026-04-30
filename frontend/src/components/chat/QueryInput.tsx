"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";

export function QueryInput({
  onSubmit,
  disabled,
  placeholder,
}: {
  onSubmit: (value: string) => void | Promise<void>;
  disabled?: boolean;
  placeholder?: string;
}) {
  const [value, setValue] = useState("");

  const submit = async () => {
    const trimmed = value.trim();
    if (!trimmed || disabled) return;
    setValue("");
    await onSubmit(trimmed);
  };

  return (
    <div className="rounded-[28px] border border-white/10 bg-[linear-gradient(180deg,rgba(16,24,38,0.96),rgba(10,15,26,0.98))] p-3 shadow-glow">
      <div className="flex flex-col gap-3 sm:flex-row">
        <Input
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder={placeholder}
          disabled={disabled}
          onKeyDown={async (event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              await submit();
            }
          }}
          className="h-12 flex-1 border-white/8 bg-transparent shadow-none focus:bg-[rgba(255,255,255,0.02)]"
        />
        <Button onClick={submit} disabled={disabled || !value.trim()} size="lg" className="sm:min-w-[11rem]">
          Run analysis
        </Button>
      </div>

      <div className="mt-2 flex flex-col gap-1 px-1 sm:flex-row sm:items-center sm:justify-between">
        <p className="text-xs text-muted-fg">
          {disabled ? "Connect a database to unlock the analytical workflow." : "Press Enter to send a question."}
        </p>
        <p className="text-[10px] uppercase tracking-[0.24em] text-muted-fg">Traceable workflow</p>
      </div>
    </div>
  );
}
