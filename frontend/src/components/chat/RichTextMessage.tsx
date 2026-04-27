"use client";

type Block =
  | { type: "paragraph"; text: string }
  | { type: "heading"; text: string }
  | { type: "bullet"; items: string[] }
  | { type: "numbered"; items: string[] };

function parseBlocks(text: string): Block[] {
  const lines = text
    .replace(/\r\n/g, "\n")
    .split("\n")
    .map((line) => line.trim());

  const blocks: Block[] = [];
  let paragraph: string[] = [];
  let listType: "bullet" | "numbered" | null = null;
  let listItems: string[] = [];

  const flushParagraph = () => {
    if (paragraph.length) {
      blocks.push({ type: "paragraph", text: paragraph.join(" ").trim() });
      paragraph = [];
    }
  };

  const flushList = () => {
    if (listType && listItems.length) {
      blocks.push({ type: listType, items: [...listItems] });
      listType = null;
      listItems = [];
    }
  };

  for (const line of lines) {
    if (!line) {
      flushParagraph();
      flushList();
      continue;
    }

    const headingMatch = line.match(/^#{1,6}\s+(.+)$/);
    if (headingMatch) {
      flushParagraph();
      flushList();
      blocks.push({ type: "heading", text: headingMatch[1].trim() });
      continue;
    }

    const bulletMatch = line.match(/^[-*]\s+(.+)$/);
    if (bulletMatch) {
      flushParagraph();
      if (listType !== "bullet") {
        flushList();
        listType = "bullet";
      }
      listItems.push(bulletMatch[1].trim());
      continue;
    }

    const numberedMatch = line.match(/^\d+\.\s+(.+)$/);
    if (numberedMatch) {
      flushParagraph();
      if (listType !== "numbered") {
        flushList();
        listType = "numbered";
      }
      listItems.push(numberedMatch[1].trim());
      continue;
    }

    flushList();
    paragraph.push(line);
  }

  flushParagraph();
  flushList();

  if (!blocks.length && text.trim()) {
    return [{ type: "paragraph", text: text.trim() }];
  }

  return blocks;
}

function renderInline(text: string) {
  const parts = text.split(/(\*\*[^*]+\*\*)/g).filter(Boolean);
  return parts.map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return (
        <strong key={index} className="font-semibold text-fg">
          {part.slice(2, -2)}
        </strong>
      );
    }
    return <span key={index}>{part}</span>;
  });
}

export function RichTextMessage({ text }: { text: string }) {
  const blocks = parseBlocks(text);

  return (
    <div className="space-y-3 text-sm leading-7 text-fg/92">
      {blocks.map((block, index) => {
        if (block.type === "heading") {
          return (
            <h4 key={index} className="pt-1 text-[11px] font-semibold uppercase tracking-[0.22em] text-accent">
              {renderInline(block.text)}
            </h4>
          );
        }

        if (block.type === "bullet") {
          return (
            <ul key={index} className="space-y-2 pl-5 text-fg/90">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex} className="list-disc marker:text-accent">
                  {renderInline(item)}
                </li>
              ))}
            </ul>
          );
        }

        if (block.type === "numbered") {
          return (
            <ol key={index} className="space-y-2 pl-5 text-fg/90">
              {block.items.map((item, itemIndex) => (
                <li key={itemIndex} className="list-decimal marker:text-accent">
                  {renderInline(item)}
                </li>
              ))}
            </ol>
          );
        }

        return (
          <p key={index} className="text-sm leading-7 text-fg/92">
            {renderInline(block.text)}
          </p>
        );
      })}
    </div>
  );
}
