import { useEffect, useId, useRef } from "react";
import ReactMarkdown from "react-markdown";
import mermaid from "mermaid";

mermaid.initialize({ startOnLoad: false, theme: "dark" });

function MermaidBlock({ code }: { code: string }) {
  const ref = useRef<HTMLDivElement>(null);
  const uid = useId().replace(/:/g, "");

  useEffect(() => {
    const el = ref.current;
    if (!el) return;
    let cancelled = false;
    mermaid
      .render(`mmd-${uid}`, code.trim())
      .then(({ svg }) => {
        if (!cancelled) el.innerHTML = svg;
      })
      .catch(() => {
        if (!cancelled) {
          el.innerHTML = `<pre class="mermaid-fallback">${code}</pre>`;
        }
      });
    return () => {
      cancelled = true;
    };
  }, [code, uid]);

  return <div className="mermaid-block" ref={ref} />;
}

type Props = { children: string };

export function MarkdownBody({ children }: Props) {
  return (
    <ReactMarkdown
      components={{
        code({ className, children: codeChildren, ...props }) {
          const match = /language-(\w+)/.exec(className || "");
          const lang = match?.[1];
          const text = String(codeChildren).replace(/\n$/, "");
          if (lang === "mermaid") {
            return <MermaidBlock code={text} />;
          }
          return (
            <code className={className} {...props}>
              {codeChildren}
            </code>
          );
        },
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
