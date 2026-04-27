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
        className="h-12 flex-1"
      />
      <Button onClick={submit} disabled={disabled || !value.trim()} size="lg">
        Ask
      </Button>
    </div>
  );
}

